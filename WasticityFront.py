import psutil
import PySimpleGUI as sg
from PIL import Image

def BatteryInfo():
    battery = psutil.sensors_battery()
    battery_percent = battery.percent
    is_power_plugged = battery.power_plugged
    seconds_till_charged = battery.secsleft
    return battery_percent, is_power_plugged, seconds_till_charged

# Define image paths for different battery levels
images = {
    "low": "Low.png",                         # 0-30%
    "mid_low": "Half Full.png",               # 30-60%
    "mid_high": "Close to full.png",          # 60-99%
    "high": "Full Battery.png",               # 100%
}

# Define the layout with a 250x250 image on the left and squares on the right
layout = [
    [
        sg.Image(images["low"], key="-IMAGE-", background_color='dark gray', expand_x=False, expand_y=False),
        sg.Push(),  # This will push the graph to the right
        sg.Push(),
        sg.Graph(
            canvas_size=(400, 300),  # Much larger canvas
            graph_bottom_left=(0, 0),
            graph_top_right=(400, 300),
            key='-GRAPH-',
            background_color='dark gray',
            pad=((50, 20), (0, 0))  # Adjusted padding for medium-sized gap
        )
    ],
    [sg.Text('', key="-TEXT-", font=('Comic Sans MS', 14), background_color='dark gray', text_color='black', pad=(30, 0))]
]

# Create the window with finalize=True
window = sg.Window('Wasticity', layout, size=(815, 380), keep_on_top=True, background_color='dark gray', finalize=True)

# Draw the initial squares
graph = window['-GRAPH-']
# Top square - much larger and further right
graph.draw_rectangle((5, 275), (350, 150), line_color='black', line_width=3)
graph.draw_text('Status', (175, 255), color='black', font=('Comic Sans MS', 18,'bold'))

warningImage={
    "alert":"Warning.png"
}

Overflow=False

Overflow=True
if Overflow:
    image_path = warningImage["alert"]
    image = Image.open(image_path)
    image = image.resize((100, 100))  # Adjust size (width, height) as needed

# Save the resized image to a temporary file
    resized_image_path = "resized_alert.png"
    image.save(resized_image_path)

# Draw the resized image on the graph
    graph.draw_image(filename=resized_image_path, location=(125, 250))



# Bottom square - much larger and further right
graph.draw_rectangle((5, 150), (350, 20), line_color='black', line_width=3)
graph.draw_text('Cost of electricity in your area', (175, 130), color='black', font=('Comic Sans MS', 14))

#This will be edited
graph.draw_text('$$$$', (175, 100), color='black', font=('Comic Sans MS', 14))

graph.draw_text('Current cost per hour', (175, 70), color='black', font=('Comic Sans MS', 14))

#This will be edited
graph.draw_text('$$$$', (175, 40), color='black', font=('Comic Sans MS', 14))



while True:
    # Read the battery info
    battery_percent, is_power_plugged, seconds_till_charged = BatteryInfo()
    
    # Default image path
    image_file = images["low"]  # Default to "Low.png"
    battery_text = f"Your battery is at {battery_percent}%"
    
    # Determine the appropriate image based on battery percentage
    if 0 <= battery_percent < 30:
        image_file = images["low"]
    elif 30 <= battery_percent < 60:
        image_file = images["mid_low"]
    elif 60 <= battery_percent < 100:
        image_file = images["mid_high"]
    elif battery_percent == 100:
        image_file = images["high"]
    
    # Update the displayed image
    window["-IMAGE-"].update(filename=image_file)
    window["-TEXT-"].update(battery_text)
    
    # Read window events
    event, values = window.read(timeout=1000)  # Update every second
    if event in (sg.WINDOW_CLOSED, 'Exit'):
        break

# Close the window when done
window.close()
