# Instructions:
# Do not change the output file names, use the helper functions as you see fit

import os
import sys
import cv2
import math
import numpy as np
import matplotlib.pyplot as plt

def help_message():
   print("Usage: [Question_Number] [Input_Options] [Output_Options]")
   print("[Question Number]")
   print("1 Perspective warping")
   print("2 Cylindrical warping")
   print("3 Bonus perspective warping")
   print("4 Bonus cylindrical warping")
   print("[Input_Options]")
   print("Path to the input images")
   print("[Output_Options]")
   print("Output directory")
   print("Example usages:")
   print(sys.argv[0] + " 1 " + "[path to input image1] " + "[path to input image2] " + "[path to input image3] " + "[output directory]")

'''
Detect, extract and match features between img1 and img2.
Using SIFT as the detector/extractor, but this is inconsequential to the user.

Returns: (pts1, pts2), where ptsN are points on image N.
    The lists are "aligned", i.e. point i in pts1 matches with point i in pts2.

Usage example:
    im1 = cv2.imread("image1.jpg", 0)
    im2 = cv2.imread("image2.jpg", 0)
    (pts1, pts2) = feature_matching(im1, im2)

    plt.subplot(121)
    plt.imshow(im1)
    plt.scatter(pts1[:,:,0],pts1[:,:,1], 0.5, c='r', marker='x')
    plt.subplot(122)
    plt.imshow(im2)
    plt.scatter(pts1[:,:,0],pts1[:,:,1], 0.5, c='r', marker='x')
'''
def feature_matching(img1, img2, savefig=False):
    # Initiate SIFT detector
    sift = cv2.xfeatures2d.SIFT_create()
    # find the keypoints and descriptors with SIFT
    kp1, des1 = sift.detectAndCompute(img1,None)
    kp2, des2 = sift.detectAndCompute(img2,None)
    # FLANN parameters
    FLANN_INDEX_KDTREE = 1
    index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
    search_params = dict(checks=50)   # or pass empty dictionary
    flann = cv2.FlannBasedMatcher(index_params,search_params)
    matches2to1 = flann.knnMatch(des2,des1,k=2)

    matchesMask_ratio = [[0,0] for i in xrange(len(matches2to1))]
    match_dict = {}
    for i,(m,n) in enumerate(matches2to1):
        if m.distance < 0.7*n.distance:
            matchesMask_ratio[i]=[1,0]
            match_dict[m.trainIdx] = m.queryIdx

    good = []
    recip_matches = flann.knnMatch(des1,des2,k=2)
    matchesMask_ratio_recip = [[0,0] for i in xrange(len(recip_matches))]

    for i,(m,n) in enumerate(recip_matches):
        if m.distance < 0.7*n.distance: # ratio
            if m.queryIdx in match_dict and match_dict[m.queryIdx] == m.trainIdx: #reciprocal
                good.append(m)
                matchesMask_ratio_recip[i]=[1,0]



    if savefig:
        draw_params = dict(matchColor = (0,255,0),
                           singlePointColor = (255,0,0),
                           matchesMask = matchesMask_ratio_recip,
                           flags = 0)
        img3 = cv2.drawMatchesKnn(img1,kp1,img2,kp2,recip_matches,None,**draw_params)

        plt.figure(),plt.xticks([]),plt.yticks([])
        plt.imshow(img3,)
        plt.savefig("feature_matching.png",bbox_inches='tight')

    return ([ kp1[m.queryIdx].pt for m in good ],[ kp2[m.trainIdx].pt for m in good ])

'''
Warp an image from cartesian coordinates (x, y) into cylindrical coordinates (theta, h)
Returns: (image, mask)
Mask is [0,255], and has 255s wherever the cylindrical images has a valid value.
Masks are useful for stitching

Usage example:

    im = cv2.imread("myimage.jpg",0) #grayscale
    h,w = im.shape
    f = 700
    K = np.array([[f, 0, w/2], [0, f, h/2], [0, 0, 1]]) # mock calibration matrix
    imcyl = cylindricalWarpImage(im, K)
'''
def cylindricalWarpImage(img1, K, savefig=False):
    f = K[0,0]

    im_h,im_w = img1.shape

    # go inverse from cylindrical coord to the image
    # (this way there are no gaps)
    cyl = np.zeros_like(img1)
    cyl_mask = np.zeros_like(img1)
    cyl_h,cyl_w = cyl.shape
    x_c = float(cyl_w) / 2.0
    y_c = float(cyl_h) / 2.0
    for x_cyl in np.arange(0,cyl_w):
        for y_cyl in np.arange(0,cyl_h):
            theta = (x_cyl - x_c) / f
            h     = (y_cyl - y_c) / f

            X = np.array([math.sin(theta), h, math.cos(theta)])
            X = np.dot(K,X)
            x_im = X[0] / X[2]
            if x_im < 0 or x_im >= im_w:
                continue

            y_im = X[1] / X[2]
            if y_im < 0 or y_im >= im_h:
                continue

            cyl[int(y_cyl),int(x_cyl)] = img1[int(y_im),int(x_im)]
            cyl_mask[int(y_cyl),int(x_cyl)] = 255


    if savefig:
        plt.imshow(cyl, cmap='gray')
        plt.savefig("cyl.png",bbox_inches='tight')

    return (cyl,cyl_mask)

'''
Calculate the geometric transform (only affine or homography) between two images,
based on feature matching and alignment with a robust estimator (RANSAC).

Returns: (M, pts1, pts2, mask)
Where: M    is the 3x3 transform matrix
       pts1 are the matched feature points in image 1
       pts2 are the matched feature points in image 2
       mask is a binary mask over the lists of points that selects the transformation inliers

Usage example:
    im1 = cv2.imread("image1.jpg", 0)
    im2 = cv2.imread("image2.jpg", 0)
    (M, pts1, pts2, mask) = getTransform(im1, im2)

    # for example: transform im1 to im2's plane
    # first, make some room around im2
    im2 = cv2.copyMakeBorder(im2,200,200,500,500, cv2.BORDER_CONSTANT)
    # then transform im1 with the 3x3 transformation matrix
    out = cv2.warpPerspective(im1, M, (im1.shape[1],im2.shape[0]), dst=im2.copy(), borderMode=cv2.BORDER_TRANSPARENT)

    plt.imshow(out, cmap='gray')
    plt.show()
'''
def getTransform(src, dst, method='affine'):
    pts1,pts2 = feature_matching(src,dst)

    src_pts = np.float32(pts1).reshape(-1,1,2)
    dst_pts = np.float32(pts2).reshape(-1,1,2)

    if method == 'affine':
        M, mask = cv2.estimateAffine2D(src_pts, dst_pts, cv2.RANSAC, ransacReprojThreshold=5.0)
        M = np.append(M, [[0,0,1]], axis=0)

    if method == 'homography':
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

    matchesMask = mask.ravel().tolist()

    return (M, pts1, pts2, mask)
   
# ===================================================
# ================ Perspective Warping ==============
# ===================================================
def Perspective_warping(im1, im2, im3):
    im1 = cv2.copyMakeBorder(im1, 200, 200, 500, 500, cv2.BORDER_CONSTANT)

    (M, pts1, pts2, mask) = getTransform(im2, im1, 'homography')

    out = cv2.warpPerspective(im2, M, (im1.shape[1], im1.shape[0]), dst=im1.copy(), borderMode=cv2.BORDER_TRANSPARENT)

    (M2, pts1, pts2, mask) = getTransform(im3, im1, 'homography')

    out = cv2.warpPerspective(im3, M2, (im1.shape[1], im1.shape[0]), dst=out.copy(), borderMode=cv2.BORDER_TRANSPARENT)

    output_image = out

    master = cv2.imread("example_output1.png", 0)
    # val = RMSD(1,output_image,master)
    # print "rmsd val is "+str(val)
    # Write out the result
    output_name = sys.argv[5] + "output_homography.png"
    cv2.imwrite(output_name, output_image)
    return True
	
def Bonus_perspective_warping(im1, im2, im3):
    im1 = cv2.copyMakeBorder(im1, 200, 200, 500, 500, cv2.BORDER_CONSTANT)

    (M, pts1, pts2, mask) = getTransform(im2, im1, 'homography')

    out = cv2.warpPerspective(im2, M, (im1.shape[1], im1.shape[0]), dst=im1.copy(), borderMode=cv2.BORDER_TRANSPARENT)

    (M2, pts1, pts2, mask) = getTransform(im3, im1, 'homography')

    out1 = cv2.warpPerspective(im3, M2, (im1.shape[1], im1.shape[0]), dst=im1.copy(), borderMode=cv2.BORDER_TRANSPARENT)
    outf = laplacian_pyramid_blending(out1,out)
    output_image = outf  # Write out the result
    output_name = sys.argv[5] + "output_homography_lpb.png"
    cv2.imwrite(output_name, output_image)

    return True

# ===================================================
# =============== Cynlindrical Warping ==============
# ===================================================
def Cylindrical_warping(im1, im2, im3):
    im1 = cv2.copyMakeBorder(im1, 50, 50, 300, 300, cv2.BORDER_CONSTANT)

    imcy1 = getcyltuple(im1)
    im1 = imcy1[0]
    imcy2 = getcyltuple(im2)
    im2 = imcy2[0]
    (M, pts1, pts2, mask) = getTransform(im2,im1)
    M = np.delete(M, (2), axis=0)

    out = cv2.warpAffine(im2, M, (im1.shape[1], im1.shape[0]), dst=im1.copy(), borderMode=cv2.BORDER_TRANSPARENT)
    outmask = cv2.warpAffine(imcy2[1], M, (im1.shape[1], im1.shape[0]), dst=imcy1[1].copy(), borderMode=cv2.BORDER_TRANSPARENT)
    for x_cyl in np.arange(0,im1.shape[0] - 1):
        for y_cyl in np.arange(0,im1.shape[1] - 1):
            if(outmask[x_cyl,y_cyl] == 255) :
                im1[x_cyl,y_cyl] = out[x_cyl,y_cyl]

    imcy3 = getcyltuple(im3)
    im3 = imcy3[0]
    (M, pts1, pts2, mask) = getTransform(im3, im1)
    M = np.delete(M, (2), axis=0)

    out = cv2.warpAffine(im3, M, (im1.shape[1], im1.shape[0]), dst=im1.copy(), borderMode=cv2.BORDER_TRANSPARENT)
    outmask = cv2.warpAffine(imcy3[1], M, (im1.shape[1], im1.shape[0]), dst=imcy1[1].copy(), borderMode=cv2.BORDER_TRANSPARENT)
    for x_cyl in np.arange(0, im1.shape[0] - 1):
        for y_cyl in np.arange(0, im1.shape[1] - 1):
            if (outmask[x_cyl, y_cyl] == 255):
                im1[x_cyl, y_cyl] = out[x_cyl, y_cyl]

    output_image = im1
    # Write out the result
    output_name = sys.argv[5] + "output_cylindrical.png"
    cv2.imwrite(output_name, output_image)

    return True

def Bonus_cylindrical_warping(im1, im2, im3):

    output_image = im1

    # Write out the result
    output_name = sys.argv[5] + "output_cylindrical_lpb.png"
    cv2.imwrite(output_name, output_image)

    return True

def getcyltuple(im):
    f = 400
    h, w = im.shape
    K = np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1]])  # mock calibration matrix
    imcy = cylindricalWarpImage(im, K)
    return imcy

def laplacian_pyramid_blending(img_in1, img_in2):

   A = img_in1[:, :img_in1.shape[0]]
   B = img_in2[:img_in1.shape[0], :img_in1.shape[0]]
   # generate Gaussian pyramid for A
   G = A.copy()
   gpA = [G]
   for i in xrange(4):
      G = cv2.pyrDown(G)
      gpA.append(G)
   # generate Gaussian pyramid for B
   G = B.copy()
   gpB = [G]
   for i in xrange(4):
      G = cv2.pyrDown(G)
      gpB.append(G)
   # generate Laplacian Pyramid for A
   lpA = [gpA[3]]
   for i in xrange(3, 0, -1):
      GE = cv2.pyrUp(gpA[i])
      cv2.resize(GE, gpA[i - 1].shape)
      L = cv2.subtract(gpA[i - 1], GE)
      lpA.append(L)
   # generate Laplacian Pyramid for B
   lpB = [gpB[3]]
   for i in xrange(3, 0, -1):
      GE = cv2.pyrUp(gpB[i])
      cv2.resize(GE, gpB[i - 1].shape)
      L = cv2.subtract(gpB[i - 1], GE)
      lpB.append(L)
   # Add left and right halves of images in each level
   LS = []
   for la, lb in zip(lpA, lpB):
      rows, cols = la.shape
      ls = np.hstack((la[:, 0:cols / 2], lb[:, cols / 2:]))
      LS.append(ls)
   # Reconstruct output
   img_out = LS[0]
   for i in xrange(1, 4):
      img_out = cv2.pyrUp(img_out)
      img_out = cv2.add(img_out, LS[i])

   return img_out
'''
This exact function will be used to evaluate your results for HW2
Compare your result with master image and get the difference, the grading
criteria is posted on Piazza
'''
def RMSD(target, master):
    # Get width, height, and number of channels of the master image
    master_height, master_width = master.shape[:2]
    master_channel = len(master.shape)

    # Get width, height, and number of channels of the target image
    target_height, target_width = target.shape[:2]
    target_channel = len(target.shape)

    # Validate the height, width and channels of the input image
    if (master_height != target_height or master_width != target_width or master_channel != target_channel):
        return -1
    else:
        total_diff = 0.0;
        master_channels = cv2.split(master);
        target_channels = cv2.split(target);

        for i in range(0, len(master_channels), 1):
            dst = cv2.absdiff(master_channels[i], target_channels[i])
            dst = cv2.pow(dst, 2)
            mean = cv2.mean(dst)
            total_diff = total_diff + mean[0]**(1/2.0)

        return total_diff;

def RMSD(questionID, target, master):
    # Get width, height, and number of channels of the master image
    master_height, master_width = master.shape[:2]
    master_channel = len(master.shape)

    # Get width, height, and number of channels of the target image
    target_height, target_width = target.shape[:2]
    target_channel = len(target.shape)

    # Validate the height, width and channels of the input image
    if (master_height != target_height or master_width != target_width or master_channel != target_channel):
        return -1
    else:
        nonZero_target = cv2.countNonZero(target)
        nonZero_master = cv2.countNonZero(master)

        if (questionID == 1):
           if (nonZero_target < 1200000):
               return -1
        elif(questionID == 2):
            if (nonZero_target < 700000):
                return -1
        else:
            return -1

        total_diff = 0.0;
        master_channels = cv2.split(master);
        target_channels = cv2.split(target);

        for i in range(0, len(master_channels), 1):
            dst = cv2.absdiff(master_channels[i], target_channels[i])
            dst = cv2.pow(dst, 2)
            mean = cv2.mean(dst)
            total_diff = total_diff + mean[0]**(1/2.0)

        return total_diff;

if __name__ == '__main__':
   question_number = -1
   
   # Validate the input arguments
   if (len(sys.argv) != 6):
      help_message()
      sys.exit()
   else: 
      question_number = int(sys.argv[1])
      if (question_number > 4 or question_number < 1):
	 print("Input parameters out of bound ...")
         sys.exit()
		 
   input_image1 = cv2.imread(sys.argv[2], 0)
   input_image2 = cv2.imread(sys.argv[3], 0)
   input_image3 = cv2.imread(sys.argv[4], 0) 

   function_launch = {
   1 : Perspective_warping(input_image1, input_image2, input_image3),
   2 : Cylindrical_warping(input_image1, input_image2, input_image3),
   3 : Bonus_perspective_warping(input_image1, input_image2, input_image3),
   4 : Bonus_cylindrical_warping(input_image1, input_image2, input_image3),
   }

   # Call the function
   function_launch[question_number]
