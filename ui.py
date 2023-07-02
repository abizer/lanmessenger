import dearpygui.dearpygui as dpg

DIMENSIONS = (800, 600)

def resize_callback(sender, data):
    DIMENSIONS[0] = data[0]
    DIMENSIONS[1] = data[1]
    dpg.configure_item("main_window", width=DIMENSIONS[0], height=DIMENSIONS[1])

def button_callback(sender, data):
    input_value = dpg.get_value("chat_input")
    dpg.configure_item("chat_input", default_value="")
    dpg.focus_item("chat_input")

    new_text = dpg.get_value('chatlog')
    if len(new_text) > 0:
        new_text += '\n'
    new_text += 'Me: ' + input_value
    dpg.configure_item('chatlog', default_value=new_text)
    dpg.set_y_scroll('text_scroll', -1.0)

dpg.create_context()
dpg.set_global_font_scale(1.25)
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
    long_text = 'Lorem ipsum' * 100  # some long text
    with dpg.child_window(tag="text_scroll", width=600, height=200):
        dpg.add_text(default_value="", tag='chatlog', wrap=500)
    dpg.add_input_text(label="##Input Text", width=600, default_value="", tag="chat_input", on_enter=True, callback=button_callback)
    dpg.add_button(label="Submit", callback=button_callback)

with dpg.handler_registry():
    dpg.set_viewport_resize_callback(resize_callback)

dpg.create_context()
dpg.create_viewport(title='LAN Messenger', width=DIMENSIONS[0], height=DIMENSIONS[1])
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
