from friend import Message, MOCK_FRIENDS
from util import clamp
import dearpygui.dearpygui as dpg
import logging

logging.basicConfig(encoding='utf-8', level=logging.INFO)

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

        self.min_font_size     = 16
        self.max_font_size     = 20
        self.current_font_size = 18

        self.active_friend = None

    def register_fonts(self):
        DEFAULT_FONT_OSX = "/System/Library/Fonts/SFNSMono.ttf"
        self.fonts = {}
        with dpg.font_registry():
            for size in range(self.min_font_size, self.max_font_size+1):
                self.fonts[size] = dpg.add_font(DEFAULT_FONT_OSX, size)
        dpg.bind_font(self.fonts[self.current_font_size])

    # Scrolls to the end of the active chat window
    def goto_most_recent_message(self):
        dpg.set_y_scroll(self.scrollable_message_box, -1.0)

    # Empties the message box.
    def clear_message_box(self):
        dpg.delete_item(self.scrollable_message_box, children_only=True)

    # User seleted a new active friend
    def on_selected_friend_changed(self, friend, force=False):
        #logging.debug("on_selected_friend_changed: quick return " % friend)
        if friend is None and self.active_friend is None:
            return
        if not force and (self.active_friend is not None and friend == self.active_friend):
            return

        self.active_friend = friend
        logging.info(f"on_selected_friend_changed: ({friend.username})")

        self.clear_message_box()
        author_me = (len(friend.username) - 2) * ' ' + "Me:"
        author_them = friend.username + ':'
        assert len(author_them) == len(author_me)

        wrap = dpg.get_item_state(self.chat_area)['rect_size'][0] - len(author_me) - 80

        for message in MOCK_FRIENDS[friend]:
            with dpg.group(horizontal=True, parent=self.scrollable_message_box):
                if message.outgoing:
                    dpg.add_text(default_value=author_me, color=(53, 116, 176))
                else:
                    dpg.add_text(default_value=author_them, color=(227, 79, 68))
                dpg.add_text(default_value=message.content, wrap=wrap)
        self.goto_most_recent_message()

    # New friend detected in the LAN, existing friend's online status changed
    def on_friends_list_changed(self):
        COLOR_ONLINE      = (149, 196, 124)
        COLOR_ONLINE_FILL = (183, 224, 162)
        COLOR_AWAY        = (237, 232, 74)
        COLOR_AWAY_FILL   = (240, 237, 165)

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
            for i, friend in enumerate(MOCK_FRIENDS.keys()):
                with dpg.group(horizontal=True):
                    with dpg.drawlist(width=self.current_font_size, height=self.current_font_size):
                        center = self.current_font_size//2+1
                        if i == 0:
                            dpg.draw_circle((center, center), center//2, color=COLOR_ONLINE, fill=COLOR_ONLINE_FILL)
                        else:
                            dpg.draw_circle((center, center), center//2, color=COLOR_AWAY, fill=COLOR_AWAY_FILL)
                    friends_list.append(dpg.add_selectable(label=friend.username))
            for item, friend in zip(friends_list, MOCK_FRIENDS.keys()):
                dpg.configure_item(item, callback=_friend_selection, user_data=(friend, friends_list))

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
            dpg.add_input_int(label="font_size", default_value=self.current_font_size, step=1, callback=_change_font_size)

    # Main app content
    def content_area(self):
        self.content_area = dpg.add_group(parent=self.main_window, horizontal=True)

        # Chatbox
        self.chat_area = dpg.add_group(parent=self.content_area, width=-200, horizontal=False)
        with dpg.group(parent=self.chat_area, horizontal=False):
            self.scrollable_message_box = dpg.add_child_window(height=-70)
            input_box = dpg.add_input_text(label="##Input Text", default_value="", tag="chat_input", on_enter=True)
            def _on_submit(sender, data):
                input = dpg.get_value(input_box).strip()
                if len(input) > 0:
                    # clear box and refocus
                    dpg.configure_item(input_box, default_value="")
                    dpg.focus_item(input_box)

                if self.active_friend is not None:
                    MOCK_FRIENDS[self.active_friend].append(Message(input, True))
                    self.on_selected_friend_changed(self.active_friend, True)

            dpg.configure_item(input_box, callback=_on_submit)
            dpg.add_button(label="Submit", callback=_on_submit)
        self.goto_most_recent_message()

        # Friends list
        with dpg.child_window(parent=self.content_area, width=-1):
            self.friends_collapsable_header = dpg.add_collapsing_header(label="LAN Friends", default_open=True)
            self.on_friends_list_changed()

    def create_layout(self):
        self.main_window = dpg.add_window(label="main_window",
                        width=self.dim.width,
                        height=self.dim.height,
                        no_close=True,
                        menubar=False,
                        no_collapse=True,
                        no_title_bar=True,
                        no_resize=True,
                        no_move=True)
        self.menu_bar()
        self.content_area()

    def reflow_layout(self):
        dpg.configure_item(self.main_window, width=self.dim.width, height=self.dim.height)
        dpg.configure_item(self.friends_collapsable_header, default_open=True)
        self.on_selected_friend_changed(self.active_friend, force=True)

    def viewport_changed_callback(self, sender, data):
        self.dim.width  = data[0]
        self.dim.height = data[1]
        logging.info(f"Viewport changed {self.dim.width, self.dim.height}")
        self.reflow_layout()

    def run(self):
        dpg.create_context()
        with dpg.handler_registry():
            dpg.set_viewport_resize_callback(self.viewport_changed_callback)
        self.register_fonts()
        self.create_layout()
        dpg.create_viewport(title='LAN Messenger',
                            width=self.dim.width,
                            height=self.dim.height,
                            min_width=self.min_dim.width,
                            min_height=self.min_dim.height)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()

if __name__ == '__main__':
    ui = UI()
    ui.run()