from pyfingerprint.pyfingerprint import PyFingerprint
# Initialize sensor (port, baud rate, default password 0xFFFFFFFF)
f = PyFingerprint('/dev/serial0', 57600, 0xFFFFFFFF, 0x00000000)

if not f.verifyPassword():
    raise Exception("Fingerprint sensor not found!")

print("Device initialized. Templates: {}/{}".format(f.getTemplateCount(), f.getStorageCapacity()))

# Enroll new fingerprint
print("Waiting for finger placement...")
while not f.readImage():
    pass
f.convertImage(0x01)                     # store image in charBuffer1
print("Remove finger")
while f.readImage():                     # wait until finger removed
    pass
print("Place same finger again...")
while not f.readImage():
    pass
f.convertImage(0x02)                     # store in charBuffer2
if f.compareCharacteristics() == 0:      # compare buffers
    raise Exception("Fingers do not match.")
f.createTemplate()                       # merge into template
position = f.storeTemplate()             # save to flash
print("Enrolled at position #{}".format(position))
