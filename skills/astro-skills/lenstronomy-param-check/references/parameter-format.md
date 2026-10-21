# Parameter-Set Format

Both scripts read one JSON object. Its structure mirrors the inputs lenstronomy's
`LensModel`, `LightModel`, `data_configure_simple` and `PSF` take: each model
list holds profile names, and the matching kwargs list holds one object per
profile, paired by position.

| Field | Required | Type | Meaning |
|-------|----------|------|---------|
| `z_lens` | yes | number | Deflector redshift |
| `z_source` | yes | number | Source redshift; must exceed `z_lens` |
| `lens_model_list` | yes | list of strings | Lens mass profiles, e.g. `["SIE", "SHEAR"]` |
| `kwargs_lens` | yes | list of objects | One object of numbers per lens profile |
| `source_model_list` | yes | list of strings | Source light profiles, e.g. `["SERSIC_ELLIPSE"]` |
| `kwargs_source` | yes | list of objects | One object of numbers per source profile |
| `kwargs_data` | yes | object | Pixel grid and noise, see below |
| `kwargs_psf` | no | object | PSF, see below; defaults to `{"psf_type": "GAUSSIAN"}` |
| `halo_mass` | no | number | Main halo mass in M_sun (checked by `--preset deeplense`) |
| `axion_mass` | no | number | Axion mass in eV (checked by `--preset deeplense`) |
| `vortex_mass` | no | number | Vortex mass in M_sun (checked by `--preset deeplense`) |

## `kwargs_data`

| Key | Required | Meaning |
|-----|----------|---------|
| `numPix` | yes | Pixels per side of the image (a whole number) |
| `deltaPix` | yes | Pixel scale in arcsec per pixel |
| `exposure_time` | no | Seconds; `null` or absent for a noiseless image |
| `background_rms` | no | Background noise per pixel; `null` or absent for noiseless |

lenstronomy 1.9.2 spells the first two `numPix` and `deltaPix`; 1.14 renamed
them `num_pix` and `delta_pix`. Either spelling is accepted here.

## `kwargs_psf`

| Key | Meaning |
|-----|---------|
| `psf_type` | `"GAUSSIAN"`, `"PIXEL"` or `"NONE"` |
| `fwhm` | Full width at half maximum in arcsec; required for `"GAUSSIAN"` |
| `pixel_size` | Should equal `deltaPix` |

lenstronomy's `PSF` has no `sigma` argument; Gaussian PSFs take `fwhm`.

## Profile parameters

| Profile | Required keys | Optional keys (default 0) |
|---------|---------------|---------------------------|
| `SIE` | `theta_E`, `e1`, `e2` | `center_x`, `center_y` |
| `SIS` | `theta_E` | `center_x`, `center_y` |
| `EPL` | `theta_E`, `gamma`, `e1`, `e2` | `center_x`, `center_y` |
| `SHEAR` | `gamma1`, `gamma2` | `ra_0`, `dec_0` |
| `NFW` | `Rs`, `alpha_Rs` | `center_x`, `center_y` |
| `SERSIC` | `amp`, `R_sersic`, `n_sersic` | `center_x`, `center_y` |
| `SERSIC_ELLIPSE` | `amp`, `R_sersic`, `n_sersic`, `e1`, `e2` | `center_x`, `center_y` |
| `GAUSSIAN` | `amp`, `sigma` | `center_x`, `center_y` |

These were introspected from each profile's `param_names` and the arguments of
its `function` method in lenstronomy 1.9.2 and 1.14.2; the two versions agree.
Angles and lengths are in arcsec. `e1` and `e2` are lenstronomy's ellipticity
components, which `param_util.phi_q2_ellipticity(phi, q)` computes from a
position angle and an axis ratio.

## Example

See [assets/example_params.json](../assets/example_params.json).
