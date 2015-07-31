
import collections
import dateutil.parser
import svgwrite


class RenderContext(object):

    event_data = {}

    stack_structure = collections.OrderedDict()

    resource_structure = {}

    stack_coords = {}

    stack_parent_map = {}

    row_number = 0

    dwg = None

    rendered = []

    start_time = None

    end_time = None


class StackRender(object):

    box_outline = '#8e8e8e'

    box_inner_failed = '#cb9191'

    box_inner = '#d2d2d2'

    pixels_per_second = 1

    pixels_per_row = 24

    label_font_size = 20

    stack = None

    stacks = None

    resources = None

    events = None

    @staticmethod
    def event_time(event):
        return dateutil.parser.parse(event.event_time)

    @staticmethod
    def stack_id(ctx, event):
        for l in event.links:
            if l['rel'] == 'stack':
                items = l['href'].split('/')
                stack_id = items[-1]
                break
        if not stack_id:
            return
        if StackRender.is_stack_event(event):
            return ctx.stack_parent_map.get(stack_id, stack_id)
        return stack_id

    @staticmethod
    def status(event):
        s = event.resource_status
        # Return everything after the first underscore
        return s[s.index('_') + 1:]

    @staticmethod
    def event_data_key(ctx, event, rel='stack'):
        return StackRender.stack_id(ctx, event), event.resource_name

    @staticmethod
    def is_stack_event(e):
        return e.resource_status_reason.startswith('Stack ')

    def build_stack_structure(self, ctx):
        for s in self.stacks:
            if s.parent:
                ctx.stack_parent_map[s.id] = s.parent

        ss = ctx.stack_structure
        for e in self.events:

            if e.resource_status.startswith('SIGNAL'):
                continue

            stack_id = self.stack_id(ctx, e)

            if stack_id not in ss:
                ss[stack_id] = collections.OrderedDict()

            stack_dict = ss[stack_id]
            if stack_id not in stack_dict:
                stack_dict[stack_id] = []
            if e.physical_resource_id not in stack_dict:
                stack_dict[e.physical_resource_id] = []
            if e.resource_name not in stack_dict:
                stack_dict[e.resource_name] = []

        # for r in self.resources:
        #     stack_id = self.stack_id(ctx, r)
        #     if stack_id not in ss:
        #         ss[stack_id] = {}
        #     ss[stack_id][r.resource_name] = []

        # yaml.safe_dump(ss, stream=sys.stderr, default_flow_style=False)

            if self.is_stack_event(e):
                event_target = stack_dict.get(e.physical_resource_id)
            else:
                event_target = stack_dict.get(e.resource_name)
            if event_target is not None:
                event_target.append(e)

    def build_event_data(self, ctx):

        ed = ctx.event_data

        def add_data(key, event=None):
            d = ed.get(key)
            if not d:
                d = {'events': []}
                ed[key] = d
            d['events'].append(event)

        for e in self.events:
            key = self.event_data_key(ctx, e)
            add_data(key, e)

    def render_event_chart(self):
        ctx = RenderContext()
        ctx.dwg = svgwrite.Drawing()
        dwg = ctx.dwg
        ctx.start_time = self.event_time(self.events[0])
        ctx.end_time = self.event_time(self.events[-1])
        self.build_stack_structure(ctx)
        self.build_event_data(ctx)

        self.render_stack(ctx, self.stack.id)
        for e in self.events:
            self.box_inner = '#4EDFEA'
            item = ctx.event_data.get(self.event_data_key(ctx, e))
            self.render_events(ctx, item['events'])

        # return ctx.stack_structure.keys()
        return dwg.tostring()

    def render_stack(self, ctx, stack_id):
        stack_items = ctx.stack_structure.get(stack_id)
        if not stack_items:
            return
        # special case render events for root stack
        self.render_events(ctx, stack_items.get(stack_id))
        # sorted_stack_items = sorted(stack_items, first_event_time)
        for item_key, event_list in stack_items.items():
            if item_key != stack_id:
                self.render_stack(ctx, item_key)
        for item_key, event_list in stack_items.items():
            self.render_events(ctx, event_list)

    def render_events(self, ctx, events):
        if not events:
            return
        key = None

        dwg = ctx.dwg
        start_event = None
        end_event = None
        label_coords = None

        # row = ctx.row_number
        # ctx.row_number += 1

        for e in events:
            key = self.event_data_key(ctx, e)
            # sys.stderr.write('key %s\n' % (key,))
            if key in ctx.rendered:
                return

            status = self.status(e)

            if status == 'IN_PROGRESS':
                if not start_event:
                    start_event = e
            if status in ('COMPLETE', 'FAILED'):
                if start_event:
                    end_event = e
                else:
                    # TODO(sbaker) handle an end event with a missing start
                    pass
            if start_event and end_event:

                row = ctx.row_number
                ctx.row_number += 1
                is_stack_event = self.is_stack_event(e)
                start_etime = self.event_time(start_event)
                end_etime = self.event_time(end_event)
                duration = end_etime - start_etime
                offset = start_etime - ctx.start_time

                if self.status(end_event) == 'FAILED':
                    fill = self.box_inner_failed
                else:
                    fill = self.box_inner
                y = row * self.pixels_per_row
                x = offset.seconds * self.pixels_per_second
                length = x + duration.seconds * self.pixels_per_second
                height = self.pixels_per_row
                dwg.add(dwg.rect((x, y), (length, height),
                                 fill=fill,
                                 stroke=self.box_outline))
                label = e.resource_name
                if label_coords is None:
                    label_coords = (x + 4, y + height - 4)
                if label_coords:
                    dwg.add(dwg.text(
                        label, label_coords, font_size=self.label_font_size))

                stack_id = self.stack_id(ctx, e)
                stack_coords = ctx.stack_coords.get(stack_id)
                if stack_coords:
                    y_offset = self.pixels_per_row / 2
                    sx, sy = stack_coords
                    dwg.add(dwg.line(
                        (x, y + y_offset),
                        (sx, y + y_offset),
                        stroke=self.box_outline))
                    dwg.add(dwg.line(
                        (sx, y + y_offset),
                        (sx, sy + y_offset),
                        stroke=self.box_outline))

                if is_stack_event:
                    ctx.stack_coords[stack_id] = (x, y)

                start_event = None
                end_event = None
        # TODO(sbaker) handle missing end event

        if key:
            ctx.rendered.append(key)
