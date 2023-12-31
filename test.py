import skyDetector as detector
import cv2 as cv
from matplotlib import pyplot as plt 
import os
import numpy as np
import time
from nightDetection import is_night

# Function to turn all subsequent column pixels to zero after the first zero pixel
def turn_subsequent_pixels_to_zero(image):
    h, w = image.shape
    for col in range(w):
        for row in range(h):
            if image[row, col] == 0:
                image[row:, col] = 0
                break
    return image

# Detect the skyline by dilating the image and subtracting the original image
def detect_skyline(img):
    dilated = cv.dilate(img, np.ones((5, 5), np.uint8), iterations=1)
    skyline = dilated - img

    return skyline

# Evaluate the accuracy of the skyline detection by taking the percentage of pixels that are the same
def evaluate(output, ground_truth):
    diff = cv.absdiff(output, ground_truth)
    diff = diff.astype(np.uint8)
    percentage = (np.count_nonzero(diff == 0) / diff.size) * 100

    return percentage

# Get the coordinates of the zero pixels in the image, to be used for drawing contours
def get_coordinates_of_zero(img):
    coordinates = []
    h, w = img.shape
    for col in range(w):
        for row in range(h):
            if img[row, col] == 0:
                coordinates.append((col, row))
                break
    return np.array(coordinates)

# If the image is classified as night, perform night processing
def night_processing(img):
    # dilate the image to expand the skyline (night skylines are usually formed by lights)
    kernel = np.ones((5,5),np.uint8)
    dilated = cv.dilate(img, kernel, iterations=3)
    dilated -= img

    # close the image to remove noise/holes in the sky region
    dilated = cv.morphologyEx(dilated, cv.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=3)
    dilated = cv.erode(dilated, np.ones((7, 7), np.uint8), iterations=1)
    
    # invert the image to make the sky regions white, convert to binary and get the coordinates of the zero pixels
    dilated = 255 - dilated
    dilated = cv.threshold(dilated, 127, 255, cv.THRESH_BINARY)[1]
    dilated_coordinates = get_coordinates_of_zero(dilated)

    # draw contours on new image, then turn all pixels under the contours to zero. Done to remove gaps between non-sky regions.
    new_image = np.zeros(dilated.shape, np.uint8)
    cv.drawContours(new_image, [dilated_coordinates], -1, (255, 255, 255), -1)
    new_image = 255 - new_image
    new_image = turn_subsequent_pixels_to_zero(new_image)
    new_image = cv.threshold(new_image, 127, 1, cv.THRESH_BINARY)[1]

    return new_image


if __name__ == "__main__":
    # time the program
    start = time.time()

    # Path to the dataset. Data folder is to store the directories to be processed. Skyline folder is to store the detected skylines.
    data_folder = "dataset/data"
    skyline_folder = "dataset/skyline"

    # Dictionary to store the results
    results = {}

    for img_folder in os.listdir(data_folder):

        print(f"Processing {img_folder}...")
        
        # variables to keep track of successful detections and number of night images
        successfull = 0
        numNights = 0

        # read and convert to binary for evaluation later
        ground_truth = cv.imread(f'dataset/ground_truth/{img_folder}_GT.png', 0)
        ground_truth = cv.threshold(ground_truth, 127, 1, cv.THRESH_BINARY)[1]

        # iterate through all images in the folder
        for img_path in os.listdir(os.path.join(data_folder, img_folder)):
            try:            
                img = cv.imread(os.path.join(data_folder, img_folder, img_path))

                # check if it is night
                isNight = is_night(img)

                img = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

                # if it is night, perform night processing. Else, perform normal processing
                if isNight:
                    numNights += 1
                    img_sky = night_processing(img)
                else:

                    img_sky = detector.get_sky_region_gradient(img)

                    img_sky = cv.morphologyEx(img_sky, cv.MORPH_CLOSE, np.ones((5, 5), np.uint8))
                    img_sky = cv.erode (img_sky, np.ones((7, 7), np.uint8), iterations=1)
                    
                    img_sky = turn_subsequent_pixels_to_zero(img_sky)


                similarity = evaluate(img_sky, ground_truth)
                if similarity > 90:
                    successfull += 1
                

                # detect and save skyline. If directory does not exist, create it
                skyline = detect_skyline(img_sky)

                if not os.path.exists(os.path.join(skyline_folder, img_folder)):
                    os.makedirs(os.path.join(skyline_folder, img_folder))
                plt.imsave(os.path.join(skyline_folder, img_folder, img_path), skyline, cmap='gray')

                # plot the images for visualisation. Comment out if not needed.
                plt.subplot(1,3,1)
                plt.imshow(ground_truth, 'gray')
                plt.title('ground truth')

                plt.subplot(1,3,2)
                plt.imshow(img_sky, 'gray')
                plt.title('Similarity: ' + str(similarity) + '%')

                plt.subplot(1,3,3)
                plt.imshow(skyline, 'gray')
                plt.title('skyline')
                plt.show()

            except Exception as e:
                print(f"Error processing {img_folder}/{img_path}: {e}")

        # calculate success rate and store in dictionary
        success_rate = successfull / len(os.listdir(os.path.join(data_folder, img_folder)))
        success_rate = round(success_rate * 100, 2)        
        results[img_folder] = success_rate

        print(f"Success rate for {img_folder}: {success_rate}%")
        print(f"Number of night images: {numNights}, Number of day images: {len(os.listdir(os.path.join(data_folder, img_folder))) - numNights}")
        

    print(results)
    print(f"Time taken: {time.time() - start} seconds")
