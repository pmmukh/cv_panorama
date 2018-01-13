# cv_panorama
Alignment and Panoramas

1. Read in the images, say input1.jpg, input2.jpg, input3.jpg
2.Apply cylindrical wrapping if needed
3.Calculate the transformation (homography for projective; affine for cylindrical) between each
4.Transform input2 and input3 to the plane of input1, and produce output.png

There is also some perspective warping done with laplacian blending, but that isn't working correctly.However, it can be used as base code by somebody.
