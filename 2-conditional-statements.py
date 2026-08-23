
# digital pet program snippet

satiety = 80

if satiety < 75:
	print("I'm hungry!")
else:
	print("I'm happy")

# closet app snippet

from enum import Enum

import matplotlib.image as mpimg
import matplotlib.pyplot as plt


class Clothing(Enum):
	COAT = 1
	JACKET = 2

# define a function
# method and function are sometimes used interchangeably, but methods are part of a class
def get_image_url(clothing):
	match clothing:
		case Clothing.COAT:
			return "images/winter_coat.png"
		case Clothing.JACKET:
			return "images/winter_jacket.png"
		case _:
			return None

temperature_outside = 25
is_windy = False
image_url = None

if temperature_outside < 30:
	image_url = get_image_url(Clothing.COAT)
elif temperature_outside < 50 and is_windy:
	image_url = get_image_url(Clothing.JACKET)
else:
	print("It's not cold, you don't need an outer layer")

if image_url is not None:
	img = mpimg.imread(image_url)

	# Render the image inside the plot canvas
	plt.imshow(img)
	plt.axis('off')  # Optional: Hides the coordinate axes grid lines
	plt.show()