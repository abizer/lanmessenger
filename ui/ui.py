from collections import deque, OrderedDict
from comms import EventMessage, EventQueue, EventType
from friend import Friend, Message
from mock import mock_network_events
from util import clamp
import dearpygui.dearpygui as dpg
import logging
import threading

# TODO(kkuehler): default to INFO and make configurable via cli argument
logging.basicConfig(encoding="utf-8", level=logging.DEBUG)


class Dimensions:
    def __init__(self, width, height):
        self.width = width
        self.height = height


class UI:
    def __init__(self):
        # Starting dimensions. Subject to change on viewport rearragement
        self.dim = Dimensions(1368, 1000)

        # Minimum size we will allow the viewport
        self.min_dim = Dimensions(800, 750)

        self.min_font_size = 16
        self.max_font_size = 20
        self.current_font_size = 18

        self.friends = OrderedDict()
        self.active_friend = None

        self.rx_queue = EventQueue()
        self.tx_queue = EventQueue()
        self.local_tx_queue = deque()

    def register_fonts(self):
        DEFAULT_FONT_OSX = "/System/Library/Fonts/SFNSMono.ttf"
        self.fonts = {}
        with dpg.font_registry():
            for size in range(self.min_font_size, self.max_font_size + 1):
                self.fonts[size] = dpg.add_font(DEFAULT_FONT_OSX, size)
        dpg.bind_font(self.fonts[self.current_font_size])

    # Scrolls to the end of the active chat window
    def goto_most_recent_message(self):
        children = dpg.get_item_children(self.message_box_container, 1)
        if len(children) > 0:
            dpg.set_y_scroll(children[0], -1.0)

    def clear_input_box(self):
        # clear box and refocus
        dpg.configure_item(self.input_box, default_value="")
        dpg.focus_item(self.input_box)

    def on_friend_discovered(self, friend: Friend):
        logging.debug(f"EVENT: FRIEND_DISCOVERED: %s" % friend.username)
        self.friends[friend] = []
        self.on_friends_list_changed()

    # User seleted a new active friend
    def on_selected_friend_changed(self, friend, force=False):
        # logging.debug("on_selected_friend_changed: quick return " % friend)
        friend_changed = False
        if self.active_friend is None or self.active_friend != friend:
            friend_changed = True

        self.active_friend = friend
        logging.info(f"on_selected_friend_changed: ({friend.username, friend_changed})")

        if friend_changed or (force and self.active_friend is not None):
            dpg.delete_item(self.message_box_container, children_only=True)
            self.scrollable_message_box = dpg.add_child_window(
                horizontal_scrollbar=True, parent=self.message_box_container
            )
            for message in self.friends[friend]:
                self.render_message(friend, message)
            self.goto_most_recent_message()
            self.clear_input_box()

    def render_message(self, friend, message):
        # unused for now in favor of the much simpler horizontal scrollbar
        # wrap = dpg.get_item_state(self.chat_area)['rect_size'][0] - len(author_me) - 80
        author_me = (len(friend.username) - 2) * " " + "Me:"
        author_them = friend.username + ":"
        assert len(author_them) == len(author_me)
        with dpg.group(horizontal=True, parent=self.scrollable_message_box):
            if message.outgoing:
                dpg.add_text(default_value=author_me, color=(53, 116, 176))
            else:
                dpg.add_text(default_value=author_them, color=(227, 79, 68))
            dpg.add_text(default_value=message.content)

    # New friend detected in the LAN, existing friend's online status changed
    def on_friends_list_changed(self):
        COLOR_ONLINE = (149, 196, 124)
        COLOR_ONLINE_FILL = (183, 224, 162)
        COLOR_AWAY = (237, 232, 74)
        COLOR_AWAY_FILL = (240, 237, 165)

        dpg.delete_item(self.friends_collapsable_header, children_only=True)
        with dpg.group(parent=self.friends_collapsable_header, horizontal=False):

            def _friend_selection(sender, app_data, user_data):
                # Only a single friend can be selected at a time
                new_active_friend = user_data[0]
                friend_items = user_data[1]
                for item in friend_items:
                    if item != sender:
                        dpg.set_value(item, False)
                self.on_selected_friend_changed(new_active_friend)

            friends_list = []
            for i, friend in enumerate(self.friends.keys()):
                with dpg.group(horizontal=True):
                    with dpg.drawlist(
                        width=self.current_font_size, height=self.current_font_size
                    ):
                        center = self.current_font_size // 2 + 1
                        if i == 0:
                            dpg.draw_circle(
                                (center, center),
                                center // 2,
                                color=COLOR_ONLINE,
                                fill=COLOR_ONLINE_FILL,
                            )
                        else:
                            dpg.draw_circle(
                                (center, center),
                                center // 2,
                                color=COLOR_AWAY,
                                fill=COLOR_AWAY_FILL,
                            )
                    friends_list.append(dpg.add_selectable(label=friend.username))
            for item, friend in zip(friends_list, self.friends.keys()):
                dpg.configure_item(
                    item, callback=_friend_selection, user_data=(friend, friends_list)
                )

    # Creates the settings menu
    def menu_bar(self):
        self.menu_bar = dpg.add_menu_bar(parent=self.main_window)
        dpg.bind_item_font(self.menu_bar, self.fonts[16])

        def _change_font_size(sender, app_data, user_data):
            new_font_size = clamp(app_data, self.min_font_size, self.max_font_size)
            dpg.configure_item(sender, default_value=new_font_size)
            self.current_font_size = new_font_size
            dpg.bind_item_font(self.content_area, self.fonts[self.current_font_size])
            self.on_friends_list_changed()

        with dpg.menu(parent=self.menu_bar, label="Settings"):
            dpg.add_input_int(
                label="font_size",
                default_value=self.current_font_size,
                step=1,
                callback=_change_font_size,
            )

    # Main app content
    def content_area(self):
        self.content_area = dpg.add_group(parent=self.main_window, horizontal=True)

        # Chatbox
        self.chat_area = dpg.add_group(
            parent=self.content_area, width=-200, horizontal=False
        )
        with dpg.group(parent=self.chat_area, horizontal=False):
            self.message_box_container = dpg.add_child_window(height=-70)
            self.input_box = dpg.add_input_text(
                label="##Input Text", default_value="", tag="chat_input", on_enter=True
            )

            def _on_submit(sender, data):
                input = dpg.get_value(self.input_box).strip()
                if len(input) > 0:
                    self.clear_input_box()
                    if self.active_friend is not None:
                        self.friends[self.active_friend].append(Message(input, True))
                        content = self.friends[self.active_friend][-1]
                        self.render_message(self.active_friend, content)
                        self.goto_most_recent_message()
                        self.enqueue_event(EventType.MESSAGE_SENT, content)

            dpg.configure_item(self.input_box, callback=_on_submit)
            dpg.add_button(label="Submit", callback=_on_submit)
        self.goto_most_recent_message()

        # Friends list
        with dpg.child_window(parent=self.content_area, width=-1):
            self.friends_collapsable_header = dpg.add_collapsing_header(
                label="LAN Friends", default_open=True
            )
            self.on_friends_list_changed()

    def create_layout(self):
        self.main_window = dpg.add_window(
            label="main_window",
            width=self.dim.width,
            height=self.dim.height,
            no_close=True,
            menubar=False,
            no_collapse=True,
            no_title_bar=True,
            no_resize=True,
            no_move=True,
        )
        self.menu_bar()
        self.content_area()

    def reflow_layout(self):
        dpg.configure_item(
            self.main_window, width=self.dim.width, height=self.dim.height
        )
        dpg.configure_item(self.friends_collapsable_header, default_open=True)
        if self.active_friend is not None:
            self.on_selected_friend_changed(self.active_friend, force=True)

    def tab_pressed_callback(self, sender, data):
        dpg.focus_item(self.input_box)

    def viewport_changed_callback(self, sender, data):
        self.dim.width = data[0]
        self.dim.height = data[1]
        logging.info(f"Viewport changed {self.dim.width, self.dim.height}")
        self.reflow_layout()

    def enqueue_event(self, type, payload):
        self.local_tx_queue.append(EventMessage(type=type, payload=payload))

    def process_rx_queue(self):
        while True:
            msg = self.rx_queue.get_nonblocking()
            if msg is None:
                break

            if msg.type == EventType.FRIEND_DISCOVERED:
                friend = msg.payload
                self.on_friend_discovered(friend)
            if msg.type == EventType.FRIEND_STATUS_CHANGED:
                pass
            if msg.type == EventType.MESSAGE_RECEIVED:
                pass

    def process_tx_queue(self):
        while len(self.local_tx_queue) > 0:
            event = self.local_tx_queue[0]  # peek
            if not self.tx_queue.put_nonblocking(event):
                break
            self.local_tx_queue.popleft()

    def run(self):
        dpg.create_context()
        with dpg.handler_registry():
            dpg.set_viewport_resize_callback(self.viewport_changed_callback)
            dpg.add_key_press_handler(
                key=dpg.mvKey_Tab, callback=self.tab_pressed_callback
            )
        self.register_fonts()
        self.create_layout()
        dpg.create_viewport(
            title="LAN Messenger",
            width=self.dim.width,
            height=self.dim.height,
            min_width=self.min_dim.width,
            min_height=self.min_dim.height,
        )
        dpg.setup_dearpygui()
        dpg.show_viewport()

        threading.Thread(
            target=mock_network_events, args=(self.rx_queue, self.tx_queue), daemon=True
        ).start()
        while dpg.is_dearpygui_running():
            self.process_rx_queue()
            self.process_tx_queue()
            dpg.render_dearpygui_frame()
        dpg.destroy_context()


if __name__ == "__main__":
    ui = UI()
    ui.run()
