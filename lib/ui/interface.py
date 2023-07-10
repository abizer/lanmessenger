from lib.util import EventQueue
from lib.ui.event import (
    EventMessage,
    EventType,
    FriendIdentifier,
    LOOPBACK_IDENTIFIER,
    Status,
)
from lib.ui.settings import Settings, Dimensions
import lib.ui.settings as settings
import lib.ui.event as event
from lib.ui.mock import mock_network_events
from lib.ui.util import clamp

from collections import deque, OrderedDict, namedtuple
from copy import deepcopy
from typing import Optional


import dearpygui.dearpygui as dpg
from enum import Enum
import logging
import threading

# TODO(kkuehler): default to INFO and make configurable via cli argument
logging.basicConfig(encoding="utf-8", level=logging.DEBUG)


CircleColor = namedtuple("CircleColor", "outline fill")


class Friend:
    class _Message:
        def __init__(self, content: str, outgoing: bool):
            self.content = content
            self.outgoing = outgoing

    def append_message(self, content: str, outgoing: bool) -> _Message:
        self.messages.append(Friend._Message(content=content, outgoing=outgoing))
        return self.messages[-1]

    def __init__(self, identifier, status=Status.ONLINE):
        self.identifier = identifier
        self.status = status
        self.has_unread = False
        self.messages = []

    def __hash__(self):
        return hash(self.identifier)

    def __eq__(self, other):
        if other == None:
            return False
        return self.identifier == other.identifier


FRIEND_LOOPBACK = Friend(LOOPBACK_IDENTIFIER)


class CustomWidget:
    COLOR_SELECTABLE_NO_BACKGROUND = (37, 37, 38)
    COLOR_SELECTABLE_CLICKED = (51, 51, 55)
    COLOR_SELECTABLE_NEW_MESSAGE = (148, 35, 166)

    COLOR_STATUS_ONLINE = CircleColor((149, 196, 124), (183, 224, 162))
    COLOR_STATUS_OFFLINE = CircleColor((201, 60, 72), (230, 83, 83))
    COLOR_STATUS_AWAY = CircleColor((237, 232, 74), (240, 237, 165))

    _cached_themes = {}

    @staticmethod
    def button_selectable_theme(background_color):
        if background_color in CustomWidget._cached_themes:
            return CustomWidget._cached_themes[background_color]

        with dpg.theme() as button_selectable_default_state:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(
                    dpg.mvThemeCol_Button,
                    background_color,
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 0, 0.5)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 2, 2)
        CustomWidget._cached_themes[background_color] = button_selectable_default_state
        return button_selectable_default_state

    @staticmethod
    def selectable_with_status(
        label, font_size, status, background_color=COLOR_SELECTABLE_NO_BACKGROUND
    ):
        def _status_to_color(status: Status) -> CircleColor:
            if status == status.ONLINE:
                return CustomWidget.COLOR_STATUS_ONLINE
            elif status == status.AWAY:
                return CustomWidget.COLOR_STATUS_AWAY
            else:
                return CustomWidget.COLOR_STATUS_OFFLINE

        padding_y = 2
        with dpg.group(horizontal=True):
            with dpg.drawlist(width=font_size, height=font_size + padding_y):
                center = font_size // 2 + 1
                color: CircleColor = _status_to_color(status)
                dpg.draw_circle(
                    (center, center + padding_y),
                    center // 2,
                    color=color.outline,
                    fill=color.fill,
                )
            b = dpg.add_button(label=label, width=-1)
            dpg.bind_item_theme(
                b,
                CustomWidget.button_selectable_theme(background_color),
            )
        return b


class UI:
    def __init__(self, settings=Settings()):
        # Starting dimensions. Subject to change on viewport rearragement
        self.settings = settings

        # Minimum size we will allow the viewport
        self.min_dim = Dimensions(800, 750)

        self.min_font_size = 16
        self.max_font_size = 20

        self.friends = OrderedDict()
        self.friends[LOOPBACK_IDENTIFIER] = FRIEND_LOOPBACK
        self.active_friend: Optional[Friend] = None

        self.rx_queue = EventQueue()
        self.tx_queue = EventQueue()
        self.local_tx_queue = deque()

    def register_fonts(self):
        DEFAULT_FONT_OSX = "/System/Library/Fonts/SFNSMono.ttf"
        self.fonts = {}
        with dpg.font_registry():
            for size in range(self.min_font_size, self.max_font_size + 1):
                self.fonts[size] = dpg.add_font(DEFAULT_FONT_OSX, size)
        dpg.bind_font(self.fonts[self.settings.font_size])

    # Scrolls to the end of the active chat window
    def goto_most_recent_message(self):
        dpg.set_y_scroll(self.message_box_container, -1.0)

    def clear_input_box(self):
        # clear box and refocus
        dpg.configure_item(self.input_box, default_value="")
        dpg.focus_item(self.input_box)

    def disable_input_if_offline(self):
        if self.active_friend.status == event.Status.ONLINE:
            dpg.configure_item(self.input_box, readonly=False, hint="")
        else:
            dpg.configure_item(self.input_box, readonly=True, hint="OFFLINE")

    def on_friend_discovered(self, friend_id: FriendIdentifier):
        logging.debug(f"EVENT: FRIEND_DISCOVERED: %s" % friend_id)
        self.friends[friend_id] = Friend(friend_id)
        self.on_friends_list_changed()

    def on_status_changed(self, friend: Friend, status: Status):
        logging.debug(f"EVENT: STATUS_CHANGED: {friend.identifier} {status.name}")
        friend.status = status
        self.on_friends_list_changed()

    # User selected a new active friend
    def on_selected_friend_changed(self, friend, force=False):
        # logging.debug("on_selected_friend_changed: quick return " % friend)
        friend_changed = False
        if self.active_friend != friend:
            friend_changed = True

        self.active_friend = friend
        self.active_friend.has_unread = False
        logging.info(
            f"on_selected_friend_changed: ({friend.identifier, friend_changed})"
        )

        if friend_changed or (force and self.active_friend is not None):
            dpg.delete_item(self.message_box_container, children_only=True)
            for message in friend.messages:
                self.render_message(friend, message)
            self.goto_most_recent_message()
            self.clear_input_box()
            self.disable_input_if_offline()

    def render_message(self, friend: Friend, message: Friend._Message):
        # unused for now in favor of the much simpler horizontal scrollbar
        # wrap = dpg.get_item_state(self.chat_area)['rect_size'][0] - len(author_me) - 80
        spaces_you = max(0, (len(friend.identifier) - len(FRIEND_LOOPBACK.identifier)))
        spaces_them = max(0, (len(FRIEND_LOOPBACK.identifier) - len(friend.identifier)))

        author_me = spaces_you * " " + "You:"
        author_them = spaces_them * " " + friend.identifier + ":"
        assert len(author_them) == len(author_me)
        with dpg.group(horizontal=True, parent=self.message_box_container):
            if message.outgoing:
                dpg.add_text(default_value=author_me, color=(53, 116, 176))
            else:
                dpg.add_text(default_value=author_them, color=(227, 79, 68))
            dpg.add_text(default_value=message.content)

    # New friend detected in the LAN, existing friend's online status changed
    def on_friends_list_changed(self):
        dpg.delete_item(self.friends_collapsable_header, children_only=True)
        with dpg.group(parent=self.friends_collapsable_header, horizontal=False):

            def _friend_selection(sender, app_data, user_data):
                new_active_friend = user_data[0]
                friend_items = user_data[1]
                for item in friend_items:
                    if item != sender:
                        theme = dpg.get_item_theme(item)
                        if theme == CustomWidget.button_selectable_theme(
                            CustomWidget.COLOR_SELECTABLE_CLICKED
                        ):
                            dpg.bind_item_theme(
                                item,
                                CustomWidget.button_selectable_theme(
                                    CustomWidget.COLOR_SELECTABLE_NO_BACKGROUND
                                ),
                            )
                    else:
                        dpg.bind_item_theme(
                            item,
                            CustomWidget.button_selectable_theme(
                                CustomWidget.COLOR_SELECTABLE_CLICKED
                            ),
                        )
                self.on_selected_friend_changed(new_active_friend)

            selectables = []
            for friend in self.friends.values():
                item = CustomWidget.selectable_with_status(
                    label=friend.identifier,
                    font_size=self.settings.font_size,
                    status=friend.status,
                )
                selectables.append(item)
            for item, friend in zip(selectables, self.friends.values()):
                dpg.configure_item(
                    item, callback=_friend_selection, user_data=(friend, selectables)
                )
                if self.active_friend == friend:
                    dpg.bind_item_theme(
                        item,
                        CustomWidget.button_selectable_theme(
                            CustomWidget.COLOR_SELECTABLE_CLICKED
                        ),
                    )
                elif friend.has_unread:
                    dpg.bind_item_theme(
                        item,
                        CustomWidget.button_selectable_theme(
                            CustomWidget.COLOR_SELECTABLE_NEW_MESSAGE
                        ),
                    )

    # Creates the settings menu
    def menu_bar(self):
        self.menu_bar = dpg.add_menu_bar(parent=self.main_window)
        dpg.bind_item_font(self.menu_bar, self.fonts[16])

        def _change_font_size(sender, app_data, user_data):
            new_font_size = clamp(app_data, self.min_font_size, self.max_font_size)
            dpg.configure_item(sender, default_value=new_font_size)
            self.settings.font_size = new_font_size
            dpg.bind_item_font(self.content_area, self.fonts[self.settings.font_size])
            self.on_friends_list_changed()

        with dpg.menu(parent=self.menu_bar, label="Settings"):
            dpg.add_input_int(
                label="Font Size",
                default_value=self.settings.font_size,
                step=1,
                callback=_change_font_size,
            )
            with dpg.group(horizontal=True):

                def _on_default_clicked(sender, app_data, user_data):
                    input_box = user_data
                    dpg.configure_item(
                        input_box, default_value=settings.DEFAULT_USERNAME
                    )

                def _on_named_changed(sender, app_data, user_data):
                    input_box = user_data
                    new_username = dpg.get_value(input_box).strip()
                    if len(new_username) > 0:
                        self.settings.username = new_username
                        self.enqueue_event(
                            EventType.USERNAME_CHANGED,
                            event.UsernameChangedPayload(username=new_username),
                        )

                input_box = dpg.add_input_text(
                    default_value=self.settings.username, hint="Username"
                )
                dpg.add_button(
                    label="Default", callback=_on_default_clicked, user_data=input_box
                )
                dpg.add_button(
                    label="Save", callback=_on_named_changed, user_data=input_box
                )

    # Main app content
    def content_area(self):
        self.content_area = dpg.add_group(parent=self.main_window, horizontal=True)

        # Chatbox
        self.chat_area = dpg.add_group(
            parent=self.content_area, width=-200, horizontal=False
        )
        with dpg.group(parent=self.chat_area, horizontal=False):
            self.message_box_container = dpg.add_child_window(
                height=-70, horizontal_scrollbar=True
            )
            self.input_box = dpg.add_input_text(
                label="##Input Text", default_value="", tag="chat_input", on_enter=True
            )

            def _on_message_submit(sender, data):
                input = dpg.get_value(self.input_box).strip()
                if len(input) > 0:
                    self.clear_input_box()
                    if self.active_friend is not None:
                        msg = self.active_friend.append_message(input, True)
                        self.render_message(self.active_friend, msg)
                        self.goto_most_recent_message()
                        self.enqueue_event(
                            EventType.MESSAGE_SENT,
                            event.ChatMessagePayload(
                                content=msg.content,
                                author=LOOPBACK_IDENTIFIER,
                                to=self.active_friend.identifier,
                            ),
                        )

            dpg.configure_item(self.input_box, callback=_on_message_submit)
            dpg.add_button(label="Submit", callback=_on_message_submit)
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
            width=self.settings.dimensions.width,
            height=self.settings.dimensions.height,
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
            self.main_window,
            width=self.settings.dimensions.width,
            height=self.settings.dimensions.height,
        )
        dpg.configure_item(self.friends_collapsable_header, default_open=True)
        if self.active_friend is not None:
            self.on_selected_friend_changed(self.active_friend, force=True)

    def tab_pressed_callback(self, sender, data):
        dpg.focus_item(self.input_box)

    def viewport_changed_callback(self, sender, data):
        self.settings.dimensions = Dimensions(width=data[0], height=data[1])
        logging.info(
            f"Viewport changed {self.settings.dimensions.width, self.settings.dimensions.height}"
        )
        self.reflow_layout()

    def enqueue_event(self, type, payload):
        self.local_tx_queue.append(EventMessage(type=type, payload=payload))

    def process_rx_queue(self):
        while True:
            msg = self.rx_queue.get_nonblocking()
            if msg is None:
                break

            if msg.type == EventType.FRIEND_STATUS_CHANGED:
                payload: event.StatusChangedPayload = msg.payload
                if payload.id not in self.friends:
                    logging.debug(f"EVENT: FRIEND_DISCOVERED: %s" % payload.id)
                    self.friends[payload.id] = Friend(payload.id)
                else:
                    f = self.friends[payload.id]
                    f.status = payload.status
                    logging.debug(
                        f"EVENT: STATUS_CHANGED: {f.identifier} {f.status.name}"
                    )
                    if f == self.active_friend:
                        self.disable_input_if_offline()
                self.on_friends_list_changed()
            if msg.type == EventType.MESSAGE_RECEIVED:
                m = self.friends[msg.payload.author].append_message(
                    content=msg.payload.content, outgoing=False
                )
                author = self.friends[msg.payload.author]
                if author == self.active_friend:
                    self.render_message(author, m)
                    self.goto_most_recent_message()
                else:
                    author.has_unread = True
                    self.on_friends_list_changed()

    def process_tx_queue(self):
        def _peekleft():
            return self.local_tx_queue[0]

        while len(self.local_tx_queue) > 0:
            event = _peekleft()
            if not self.tx_queue.put_nonblocking(event):
                break
            self.local_tx_queue.popleft()

    def run(self, mock=False):
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
            width=self.settings.dimensions.width,
            height=self.settings.dimensions.height,
            min_width=self.min_dim.width,
            min_height=self.min_dim.height,
        )
        dpg.setup_dearpygui()
        dpg.show_viewport()

        if mock:
            threading.Thread(
                target=mock_network_events,
                args=(self.rx_queue, self.tx_queue),
                daemon=True,
            ).start()
        while dpg.is_dearpygui_running():
            self.process_rx_queue()
            self.process_tx_queue()
            dpg.render_dearpygui_frame()
        dpg.destroy_context()
        self.settings.serialize()
