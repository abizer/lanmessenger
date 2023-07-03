import dearpygui.dearpygui as dpg
from enum import Enum
from collections import OrderedDict
import uuid
import random

class Friend:
    class Status(Enum):
        # Sending discovery pings and activity pings within past 15 minutes
        ONLINE = 1   
        # Sending discovery pings but no recent activity pings
        AWAY   = 2 
        # Not sending discovery pings 
        OFFLINE = 3

    def __init__(self, username, uuid=uuid.uuid4(), status=Status.ONLINE):
        self.username = username
        self.status = status
        self.uuid = uuid

    def __hash__(self):
        return hash(self.uuid)

    def __eq__(self, other):
        return self.username == other.username and self.uuid == other.uuid

class Message:
    def __init__(self, content, outgoing):
        self.content = content
        self.outgoing = outgoing

abizer = Friend("Abizer")
liam   = Friend("Liam")
rachel = Friend("Rachel")

friend_buffers = OrderedDict()
friend_buffers[abizer] = []
friend_buffers[liam] = []
friend_buffers[rachel] = []

def fill_stub_data():
    stub_text = []
    with open("declaration.txt") as f:
        for line in f.readlines():
            l = line.strip()
            if len(l) > 0:
                stub_text.append(l)

    max_line = len(stub_text)

    for friend, message_buffer in friend_buffers.items():
        num_sent = random.randrange(10, 20)
        num_recv = random.randrange(10, 20)
        
        sent_start = random.randrange(0, max_line-1)
        recv_start = random.randrange(0, max_line-1)

        outgoing = [ Message(d, True) for d in stub_text[sent_start:] ]
        incoming = [ Message(d, False) for d in stub_text[recv_start:] ]
        while len(outgoing) > 0 and len(incoming) > 0:
            if random.random() > 0.5:
                friend_buffers[friend].append(outgoing.pop())
            else:
                friend_buffers[friend].append(incoming.pop())
        while len(incoming) > 0:
                friend_buffers[friend].append(incoming.pop())
        while len(outgoing) > 0:
                friend_buffers[friend].append(outgoing.pop())


DIMENSIONS = [1368, 1000]
FONT_SCALE = 1.25

def clamp(num, min_value, max_value):
   return max(min(num, max_value), min_value)

def adjust_layout():
    pals_window_width = 200
    padding = 20
    new_chatbox_width = DIMENSIONS[0] - pals_window_width - padding
    dpg.configure_item("chatbox", width=new_chatbox_width)
    dpg.configure_item("text_scroll", height=int(DIMENSIONS[1]*0.6))
    dpg.configure_item("pals_list", width=pals_window_width)

    print(DIMENSIONS[0], DIMENSIONS[1])

def viewport_changed_callback(sender, data):
    DIMENSIONS[0] = data[0]
    DIMENSIONS[1] = data[1]
    dpg.configure_item("main_window", width=DIMENSIONS[0], height=DIMENSIONS[1])
    adjust_layout()


def button_callback(sender, data):
    input_value = dpg.get_value("chat_input")
    if len(input_value) > 0:
        dpg.configure_item("chat_input", default_value="")

        new_text = dpg.get_value('chatlog')
        if len(new_text) > 0:
            new_text += '\n'
        new_text += 'Me: ' + input_value
        dpg.configure_item('chatlog', default_value=new_text)
    dpg.focus_item("chat_input")
    dpg.set_y_scroll('text_scroll', -1.0)

dpg.create_context()

dpg.set_global_font_scale(FONT_SCALE)
with dpg.handler_registry():
    dpg.set_viewport_resize_callback(viewport_changed_callback)

DEFAULT_FONT_INDEX = 4
MENU_FONT_INDEX    = 2

fill_stub_data()

fonts = {} 
MIN_FONT_SIZE = 12
MAX_FONT_SIZE = 24
DEFAULT_FONT_SIZE = 16
MENU_FONT_SIZE = 14 # not configurable

with dpg.font_registry():
    for i in range(MIN_FONT_SIZE, MAX_FONT_SIZE+1):
        fonts[i] = dpg.add_font("/System/Library/Fonts/SFNSMono.ttf", i)

with dpg.window(label="main", 
                tag="main_window", 
                width=DIMENSIONS[0], 
                height=DIMENSIONS[1], 
                no_close=True, 
                menubar=False, 
                no_collapse=True, 
                no_title_bar=True, 
                no_resize=True, 
                no_move=True):

    with dpg.menu_bar():
        with dpg.menu(tag="MainMenu", label="Setting"):
            def _change_font_size(sender, app_data, user_data):
                font_size = clamp(app_data, MIN_FONT_SIZE, MAX_FONT_SIZE)
                dpg.configure_item("SettingFontScale", default_value=font_size)

                current_font = dpg.get_item_font("main_area")
                if current_font != fonts[font_size]:
                    dpg.bind_item_font("main_area", fonts[font_size])

            dpg.add_input_int(label="Font Size", tag="SettingFontScale", callback=_change_font_size, default_value=DEFAULT_FONT_SIZE, step=1)

    with dpg.group(tag="main_area", horizontal=True):
        with dpg.group(tag="chatbox", horizontal=False):
            with dpg.child_window(tag="text_scroll", height=int(DIMENSIONS[1]*0.6)):
                padding = 20
                wrap = dpg.get_item_width("text_scroll") - padding
                # this sucks. We should have a horizontal group with a text for
                # the username and a separate text for each message....
                dpg.add_text(default_value="", tag='chatlog', wrap=wrap)
            dpg.add_input_text(label="##Input Text", width=600, default_value="", tag="chat_input", on_enter=True, callback=button_callback)
            dpg.add_button(label="Submit", callback=button_callback)


        with dpg.child_window(tag="pals_list", width=200):
            with dpg.collapsing_header(label="LAN pals", default_open=True):
                with dpg.group(horizontal=False):
                    def _single_selection(sender, app_data, user_data):
                        pals = user_data[0]
                        friend = user_data[1]
                        for p in pals:
                            if p != sender:
                                dpg.set_value(p, False)

                        dpg.delete_item("text_scroll", children_only=True)

                        spaces = len(friend.username) - 2
                        fromyou = spaces * ' ' + "Me:"
                        fromthem = f'{friend.username}:'
                        padding = 20
                        wrap = dpg.get_item_width("text_scroll") - padding
                        for message in friend_buffers[friend]:
                            with dpg.group(horizontal=True, parent="text_scroll"):
                                if message.outgoing:
                                    dpg.add_text(default_value=fromyou, color=(53, 116, 176))
                                else:
                                    dpg.add_text(default_value=fromthem, color=(227, 79, 68))
                                dpg.add_text(default_value=message.content, wrap=wrap-6)
                        dpg.set_y_scroll('text_scroll', -1.0)

                    pals = [ dpg.add_selectable(label=friend.username) for friend in friend_buffers.keys() ]
                    for pal, friend in zip(pals, friend_buffers):
                        dpg.configure_item(pal, callback=_single_selection, user_data=(pals, friend))

dpg.bind_font(fonts[DEFAULT_FONT_SIZE])
dpg.bind_item_font("MainMenu", fonts[MENU_FONT_SIZE])

dpg.create_viewport(title='LAN Messenger', width=DIMENSIONS[0], height=DIMENSIONS[1], min_width=800, min_height=600)
dpg.setup_dearpygui()
dpg.show_viewport()
adjust_layout()
dpg.start_dearpygui()
dpg.destroy_context()
