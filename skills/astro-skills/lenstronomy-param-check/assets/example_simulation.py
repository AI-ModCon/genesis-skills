"""Render the lensed image described by example_params.json with lenstronomy.

Every value is written as a literal, so check_code_params.py can verify it.
Works with lenstronomy 1.9.2 and 1.14: data_configure_simple takes the pixel
count and scale positionally, and its keyword names differ between them.

Usage: python3 example_simulation.py [output.npy]
"""

import sys

import numpy as np
import lenstronomy.Util.simulation_util as sim_util
from lenstronomy.Data.imaging_data import ImageData
from lenstronomy.Data.psf import PSF
from lenstronomy.ImSim.image_model import ImageModel
from lenstronomy.LensModel.lens_model import LensModel
from lenstronomy.LightModel.light_model import LightModel

numPix = 64
deltaPix = 0.08
kwargs_data = sim_util.data_configure_simple(
    numPix, deltaPix, exposure_time=5400.0, background_rms=0.01
)
data_class = ImageData(**kwargs_data)
psf_class = PSF(psf_type="GAUSSIAN", fwhm=0.15, pixel_size=deltaPix)

lens_model_list = ["SIE"]
kwargs_lens = [{"theta_E": 1.0, "e1": 0.1, "e2": 0.0, "center_x": 0.0, "center_y": 0.0}]
source_model_list = ["SERSIC_ELLIPSE"]
kwargs_source = [
    {"amp": 12.0, "R_sersic": 0.3, "n_sersic": 1.5, "e1": 0.1, "e2": 0.0,
     "center_x": 0.05, "center_y": 0.05}
]

image_model = ImageModel(
    data_class,
    psf_class,
    lens_model_class=LensModel(lens_model_list=lens_model_list),
    source_model_class=LightModel(light_model_list=source_model_list),
    kwargs_numerics={"supersampling_factor": 1},
)
image = image_model.image(kwargs_lens=kwargs_lens, kwargs_source=kwargs_source)

out = sys.argv[1] if len(sys.argv) > 1 else "lensed_image.npy"
np.save(out, image)
print(f"saved {image.shape} image to {out} (peak {image.max():.4g})")
