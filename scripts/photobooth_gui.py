'''
Open source photo booth.

Kevin Osborn and Justin Shaw
WyoLum.com
'''

## imports
import time
from Tkinter import *
import tkMessageBox
import ImageTk
from mailfile import *
import custom
import Image
import config
from constants import *

## This is a simple GUI, so we allow the root singleton to do the legwork
root = Tk()

### booth cam may need to present a file dialog gui.  So import after root is defined.
from boothcam import *

## set display geometry
WIDTH = 1366
HEIGHT = 788

## set photo size to fit nicely in screen
SCALE = 1.25 ### was 2

## the countdown starting value
# COUNTDOWN1 = custom.countdown1 ### use custom.countdown1 reference directly

## put the status widget below the displayed image
STATUS_H_OFFSET = 150 ## was 210

## only accept button inputs from the AlaMode when ready
Button_enabled = False

import signal
TIMEOUT = .3 # number of seconds your want for timeout

last_snap = time.time()

def interrupted(signum, frame):
    "called when serial read times out"
    print 'interrupted!'
    signal.signal(signal.SIGALRM, interrupted)

def display_image(im=None):
    '''
    display image im in GUI window
    '''
    global image_tk
    
    x,y = im.size
    x = int(x / SCALE)
    y = int(y / SCALE)

    im = im.resize((x,y));
    image_tk = ImageTk.PhotoImage(im)

    ## delete all canvas elements with "image" in the tag
    can.delete("image")
    can.create_image([(WIDTH + x) / 2 - x/2,
                      0 + y / 2], 
                     image=image_tk, 
                     tags="image")

def timelapse_due():
    '''
    Return true if a time lapse photo is due to be taken (see custom.TIMELAPSE)
    '''
    if custom.TIMELAPSE > 0:
        togo = custom.TIMELAPSE - (time.time() - last_snap)
        timelapse_label.config(text=str(int(togo)))
        out = togo < 0
    else:
        out = False
    return out

def check_and_snap(force=False, countdown1=None):
    '''
    Check button status and snap a photo if button has been pressed.

    force -- take a snapshot regarless of button status
    countdown1 -- starting value for countdown timer
    '''
    global  image_tk, Button_enabled, last_snap, signed_in
    
    if countdown1 is None:
        countdown1 = custom.countdown1
    if signed_in:
        send_button.config(state=NORMAL)
        etext.config(state=NORMAL)
    else:
        send_button.config(state=DISABLED)
        etext.config(state=DISABLED)
    if (Button_enabled == False):
        ## inform alamode that we are ready to receive button press events
        ## ser.write('e') #enable button (not used)
        Button_enabled = True
        # can.delete("text")
        # can.create_text(WIDTH/2, HEIGHT - STATUS_H_OFFSET, text="Press button when ready", font=custom.CANVAS_FONT, tags="text")
        # can.update()
        
    ## get command string from alamode
    command = ser.readline().strip()
    if Button_enabled and (force or command == "snap" or timelapse_due()):
        ## take a photo and display it
        Button_enabled = False
        can.delete("text")
        can.update()
        
        if timelapse_due():
            countdown1 = 0
        im = snap(can, countdown1=countdown1, effect=effect_var.get())
        setLights(r_var.get(), g_var.get(), b_var.get())
        if im is not None:
            last_snap = time.time()
            display_image(im)
            can.delete("text")
            can.create_text(WIDTH/2, HEIGHT - STATUS_H_OFFSET, text="Uploading Image", font=custom.CANVAS_FONT, tags="text")
            can.update()
            if signed_in:
                try:
                    googleUpload(custom.PROC_FILENAME)
                except Exception, e:
                    tkMessageBox.showinfo("Upload Error", str(e) + '\nalbumID set?')
                    # signed_in = False
            can.delete("text")
            can.create_text(WIDTH/2, HEIGHT - STATUS_H_OFFSET, text="Press button when ready", font=custom.CANVAS_FONT, tags="text")
            can.update()
    else:
        ### what command did we get?
        if command.strip():
            print command
    if not force:
        ## call this function again in 100 ms
        root.after_id = root.after(100, check_and_snap)

## for clean shutdowns
root.after_id = None
def on_close(*args, **kw):
    '''
    when window closes cancel pending root.after() call
    '''
    if root.after_id is not None:
        root.after_cancel(root.after_id)

    ### turn off LEDs
    r_var.set(0)
    g_var.set(0)
    b_var.set(0)
    root.quit()
root.protocol('WM_DELETE_WINDOW', on_close)

def force_snap(countdown1=None):
    if countdown1 is None:
        countdown1 = custom.countdown1
    check_and_snap(force=True, countdown1=countdown1)

#if they enter an email address send photo. add error checking
def sendPic(*args):
    if signed_in:
        print 'sending photo by email to %s' % email_addr.get()
        try:
            sendMail(email_addr.get().strip(),custom.emailSubject,custom.emailMsg, custom.PROC_FILENAME)
            etext.delete(0, END)
            etext.focus_set()
        except Exception, e:
            print 'Send Failed'
            can.delete("all")
            can.create_text(WIDTH/2, HEIGHT - STATUS_H_OFFSET, text="Send Failed", font=custom.CANVAS_FONT, tags="text")
            can.update()
            time.sleep(1)
            can.delete("all")
            im = Image.open(custom.PROC_FILENAME)
            display_image(im)
            can.create_text(WIDTH/2, HEIGHT - STATUS_H_OFFSET, text="Press button when ready", font=custom.CANVAS_FONT, tags="text")
            can.update()
    else:
        print 'Not signed in'

ser = findser()

def delay_timelapse(*args):
    '''
    Prevent a timelapse snapshot when someone is typeing an email address
    '''
    global last_snap
    last_snap = time.time()

#bound to text box for email
email_addr = StringVar()
email_addr.trace('w', delay_timelapse)

## bound to RGB sliders
r_var = IntVar()
g_var = IntVar()
b_var = IntVar()

## send RGB changes to alamode
def on_rgb_change(*args):
    setLights(r_var.get(), g_var.get(), b_var.get())

## call on_rgb_change when any of the sliders move
r_var.trace('w', on_rgb_change)
g_var.trace('w', on_rgb_change)
b_var.trace('w', on_rgb_change)

w, h = root.winfo_screenwidth(), root.winfo_screenheight()

# root.overrideredirect(1)
root.geometry("%dx%d+0+0" % (WIDTH, HEIGHT))
root.focus_set() # <-- move focus to this widget
frame = Frame(root)

# Button(frame, text="Exit", command=on_close).pack(side=LEFT)
Button(frame, text="Customize", command=lambda *args: custom.customize(root)).pack(side=LEFT)
send_button = Button(frame, text="SendEmail", command=sendPic, font=custom.BUTTON_FONT)
send_button.pack(side=RIGHT)

if custom.TIMELAPSE > 0:
    timelapse_label = Label(frame, text=custom.TIMELAPSE)
else:
    timelapse_label = Label(frame, text='')
timelapse_label.pack(side=LEFT)

## add a text entry box for email addresses
etext = Entry(frame,width=40, textvariable=email_addr, font=custom.BUTTON_FONT)
etext.pack()
frame.pack()

def labeled_slider(parent, label, from_, to, side, variable):
    frame = Frame(parent)
    Label(frame, text=label).pack(side=TOP)
    scale = Scale(frame, from_=from_, to=to, variable=variable, resolution=1).pack(side=TOP)
    frame.pack(side=side)
    return scale

## add a software button in case hardware button is not available
interface_frame = Frame(root)

effect_var = StringVar()
effect_var.set("0") # initialize

for effect in EFFECTS:
    b = Radiobutton(interface_frame, text=effect,
                    variable=effect_var, value=effect)
    b.pack(anchor=W)
effect_var.set('None')

rgb_frame = Frame(interface_frame)
r_slider = labeled_slider(rgb_frame, 'R', from_=0, to=255, side=LEFT, variable=r_var)
g_slider = labeled_slider(rgb_frame, 'G', from_=0, to=255, side=LEFT, variable=g_var)
b_slider = labeled_slider(rgb_frame, 'B', from_=0, to=255, side=LEFT, variable=b_var)

rgb_frame.pack(side=TOP)
snap_button = Button(interface_frame, text="*snap*", command=force_snap, font=custom.BUTTON_FONT)
snap_button.pack(side=RIGHT)
interface_frame.pack(side=RIGHT)

## the canvas will display the images
can = Canvas(root, width=WIDTH, height=HEIGHT)
can.pack()

## sign in to google?
if custom.SIGN_ME_IN:
    signed_in = setup_google()
else:
    signed_in = False
if not signed_in:
    send_button.config(state=DISABLED)
    etext.config(state=DISABLED)

### take the first photo (no delay)
can.delete("text")
can.create_text(WIDTH/2, HEIGHT/2, text="SMILE ;-)", font=custom.CANVAS_FONT, tags="splash")
can.update()
force_snap(countdown1=0)

### check button after waiting for 200 ms
root.after(200, check_and_snap)
root.wm_title("Wyolum Photobooth")
etext.focus_set()
# etext.bind("<Enter>", sendPic)
on_rgb_change()
root.mainloop()
