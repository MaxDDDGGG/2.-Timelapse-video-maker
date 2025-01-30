import cv2
import time
import os
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import threading
from PIL import Image, ImageTk

# Global variables
frame_interval = 1
video_duration = 10
frame_list = []
cap = None
frame_width = None
frame_height = None
should_stop = False
start_time = None
feed_thread = None

def log(msg):
    """Log messages with timestamps."""
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}")

def media_setup():
    """Set up the media directories and files."""
    start_time_func = time.time()
    global photo_dir, output_file, id
    media_dir = "media"
    os.makedirs(media_dir, exist_ok=True)

    existing_videos = [f for f in os.listdir(media_dir) if f.endswith("video.avi")]
    id = len(existing_videos) + 1
    output_file = os.path.join(media_dir, f"{id}_video.avi")
    photo_dir = f"media/{id}_photos"

    os.makedirs(photo_dir, exist_ok=True)

    log("Media setup completed.")
    log(f"Media setup time: {time.time() - start_time_func} seconds.")

def initialize_camera(camera_index):
    """Efficiently initialize the camera and minimize delays."""
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"Failed to open camera {camera_index}")
        return None
    print(f"Successfully opened camera {camera_index}")
    return cap

def start_timelapse():
    """Start the timelapse in a separate thread."""
    def run_timelapse():
        global cap, frame_interval, video_duration, should_stop, start_time, frame_width, frame_height, output_file, photo_dir, id, frame_list
        start_time_func = time.time()

        media_setup()

        if cap is None or not cap.isOpened():
            cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)  # Use DirectShow for better compatibility on Windows
            log("Trying to initialize camera 1...")
            time.sleep(1)  # Allow some time for initialization
            
            if not cap.isOpened():
                log("Camera 1 not available, trying camera 0...")
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Try using camera index 0
        
            time.sleep(1)  # Allow camera 0 to initialize
            if not cap.isOpened():
                messagebox.showerror("Error", "No available camera found.")
                log("No cameras found after attempting both indices.")
                return

        log("Starting timelapse...")
        should_stop = False
        frame_list = []
        start_time = time.time()  # Track start time for the timelapse

        # Show confirmation that the timelapse has started
        status_label.config(text="Timelapse Running!")

        # Start the timer from the moment the timelapse begins
        def update_timer():
            """Update the timer label periodically."""
            elapsed_time = int(time.time() - start_time)
            timer_label.config(text=f"Elapsed Time: {elapsed_time}s")
            if not should_stop:
                root.after(1000, update_timer)  # Update every second

        # Ensure correct frame size
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        log(f"Frame size: {frame_width}x{frame_height}")

        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(output_file, fourcc, 1, (frame_width, frame_height), isColor=True)

        # Start updating the timer label
        update_timer()

        while (time.time() - start_time) < video_duration and not should_stop:
            capture_time = time.time()

            ret, frame = cap.read()
            if not ret:
                log("Failed to capture frame. Exiting timelapse.")
                return

            elapsed_time = int(time.time() - start_time)
            cv2.putText(frame, f'Time: {elapsed_time}s', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

            if photo_dir:
                cv2.imwrite(f"{photo_dir}/Photo_{elapsed_time}.jpg", frame)
                frame_list.append(frame)
                log(f"Captured frame at {elapsed_time} seconds")
            else:
                log("photo_dir not defined. Skipping frame save.")

            out.write(frame)  # Write frame to video file
            while time.time() - capture_time < frame_interval:
                time.sleep(1)
        
        out.release()
        log(f"Timelapse saved as {output_file}")
        messagebox.showinfo("Timelapse Finished", f"Timelapse saved as {output_file}")
        stop_timelapse()

    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)

    threading.Thread(target=run_timelapse, daemon=True).start()

def stop_timelapse():
    """Stop the timelapse and reset UI elements."""
    global should_stop, frame_list, cap
    start_time_func = time.time()
    should_stop = True
    log("Timelapse stopped manually.")

    if cap:
        cap.release()

    # Clear the camera feed and reset UI elements
    root.after(0, lambda: camera_label.config(image=''))
    root.after(0, lambda: timer_label.config(text="Elapsed Time: 0s"))
    root.after(0, lambda: start_button.config(state=tk.NORMAL))  # Enable start button
    root.after(0, lambda: stop_button.config(state=tk.DISABLED))  # Disable stop button

    log(f"Stop timelapse function duration: {time.time() - start_time_func} seconds.")

def start_camera_thread(camera_index, callback):
    """Initialize camera in a separate thread."""
    def thread_func():
        cap = initialize_camera(camera_index)
        if cap:
            callback(cap)  # Call the callback with the initialized camera
        else:
            print("Failed to initialize the camera.")
    
    threading.Thread(target=thread_func).start()

def show_camera_feed(cap, camera_label):
    """Function to continuously update camera feed in a separate thread."""
    while True:
        ret, frame = cap.read()
        if not ret:
            log("Failed to capture frame.")
            break
        
        # Convert frame to image format suitable for Tkinter
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        img = ImageTk.PhotoImage(image=img)
        
        # Update camera label in the Tkinter window
        camera_label.config(image=img)
        camera_label.image = img  # Keep a reference to the image
        time.sleep(0.03)

def on_approve_changes_button_click():
    """Approve the changes made to the settings."""
    start_time_func = time.time()
    global frame_interval, video_duration
    try:
        frame_interval = int(frame_interval_entry.get())
        video_duration = int(video_duration_entry.get())
        messagebox.showinfo("Settings Updated", "Frame interval and video duration have been updated!")
        log(f"Settings updated: Frame Interval = {frame_interval}s, Video Duration = {video_duration}s")
    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter valid numbers for the frame interval and video duration.")
        log("Invalid input for settings.")

    log(f"Approve changes duration: {time.time() - start_time_func} seconds.")

# UI setup
root = tk.Tk()  # Create root window first
root.title("Timelapse Recorder")
status_label = tk.Label(root, text="", font=('Helvetica', 14))
status_label.pack(pady=5)

# Create the camera label widget
camera_label = tk.Label(root)
camera_label.pack(pady=5)

# Create the frame interval input field
frame_interval_label = tk.Label(root, text="Frame Interval (seconds):")
frame_interval_label.pack(pady=5)
frame_interval_entry = tk.Entry(root)
frame_interval_entry.insert(tk.END, str(frame_interval))
frame_interval_entry.pack(pady=2)

# Create the video duration input field
video_duration_label = tk.Label(root, text="Video Duration (seconds):")
video_duration_label.pack(pady=5)
video_duration_entry = tk.Entry(root)
video_duration_entry.insert(tk.END, str(video_duration))
video_duration_entry.pack(pady=2)

# Create the timer label
timer_label = tk.Label(root, text="Elapsed Time: 0s", font=('Helvetica', 14))
timer_label.pack(pady=5)

# Create the start button
start_button = tk.Button(root, text="Start Timelapse", state=tk.NORMAL, command=start_timelapse)
start_button.pack(pady=2)

# Create the stop button
stop_button = tk.Button(root, text="Stop Timelapse", command=stop_timelapse)
stop_button.pack(pady=2)

# Create the approve changes button
approve_changes_button = tk.Button(root, text="Approve Changes", command=on_approve_changes_button_click)
approve_changes_button.pack(pady=2)

# Create the show feed button
camera_index = 1
show_feed_button = tk.Button(root, text="Show Camera Feed", command=lambda: start_camera_thread(camera_index, lambda cap: show_camera_feed(cap, camera_label)))
show_feed_button.pack(pady=2)

log("Application started.")

# Start the Tkinter event loop
root.mainloop()

cv2.destroyAllWindows()
