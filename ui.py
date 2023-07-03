import dearpygui.dearpygui as dpg
from enum import Enum

class Friend:
    class Status(Enum):
        # Sending discovery pings and activity pings within past 15 minutes
        ONLINE = 1   
        # Sending discovery pings but no recent activity pings
        AWAY   = 2 
        # Not sending discovery pings 
        OFFLINE = 3

    def __init__(self, username, status=Status.ONLINE):
        self.username = username
        self.message_buffer = ""
        self.status = status

DIMENSIONS = [800, 600]
FONT_SCALE = 1.25

def clamp(num, min_value, max_value):
   return max(min(num, max_value), min_value)

def adjust_layout():
    pals_window_width = 200
    padding = 20
    new_chatbox_width = DIMENSIONS[0] - pals_window_width - padding
    dpg.configure_item("chatbox", width=new_chatbox_width)
    dpg.configure_item("pals_list", width=pals_window_width)

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
fonts = []
with dpg.font_registry():
    for i in range(12, 19):
        fonts.append(dpg.add_font("/System/Library/Fonts/SFNSMono.ttf", i))

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
                font_size = clamp(app_data, 12, 18)
                dpg.configure_item("SettingFontScale", default_value=font_size)

                print("New font size: ", font_size, font_size-12, len(fonts))
                dpg.bind_font(fonts[4])
                #dpg.bind_item_font("MainMenu", fonts[MENU_FONT_INDEX])

                #dpg.set_global_font_scale(FONT_SCALE)
                #dpg.bind_item_font("MainMenu", fixed_font)


            dpg.add_input_int(label="Font Size", tag="SettingFontScale", callback=_change_font_size, default_value=12+DEFAULT_FONT_INDEX, step=1)

    with dpg.group(horizontal=True):
        with dpg.group(tag="chatbox", horizontal=False):
            with dpg.child_window(tag="text_scroll", height=400):
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
                        pals = user_data
                        for p in pals:
                            if p != sender:
                                dpg.set_value(p, False)
                    pals = [ dpg.add_selectable(label=f"Pal {i}") for i in range(10) ]
                    for p in pals:
                        dpg.configure_item(p, callback=_single_selection, user_data=pals)

dpg.bind_font(fonts[DEFAULT_FONT_INDEX])
dpg.bind_item_font("MainMenu", fonts[MENU_FONT_INDEX])

dpg.create_viewport(title='LAN Messenger', width=DIMENSIONS[0], height=DIMENSIONS[1], min_width=800, min_height=600)
dpg.setup_dearpygui()
dpg.show_viewport()
adjust_layout()
dpg.start_dearpygui()
dpg.destroy_context()
