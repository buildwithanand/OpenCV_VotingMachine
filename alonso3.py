import cv2

cap = cv2.VideoCapture(0)

ret, frame1 = cap.read()
ret, frame2 = cap.read()

while True:
    diff = cv2.absdiff(frame1, frame2)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
    
    motion = cv2.countNonZero(thresh)

    if motion > 5000:   # adjust sensitivity
        print("Motion detected 🔥")
        
        # 👉 YOUR FACE RECOGNITION CODE HERE
        # capture → verify → send signal
        
        break   # or continue based on your logic

    frame1 = frame2
    ret, frame2 = cap.read()
