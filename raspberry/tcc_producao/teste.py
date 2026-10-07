import cv2

rtsp_url = "rtsp://admin:admin123@192.168.1.200:554/cam/realmonitor?channel=1&subtype=1"
cap =  cv2.VideoCapture(rtsp_url)
if cap.isOpened():
	ret, frame = cap.read()
	cv2.imwrite("teste.jpg", frame)
	print("Sucessso")
else:
	print("Falha na conexão com o DVR.")
cap.release()
