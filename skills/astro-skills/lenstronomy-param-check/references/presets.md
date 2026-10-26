# Presets and Where Their Bounds Come From

`validate_params.py --preset NAME` picks a set of bounds. Any single bound can
be overridden with `--set NAME=VALUE`, using the names in the first column.

| Bound | `general` | `deeplense` |
|-------|-----------|-------------|
| `z_lens_max` | 5 | 5 |
| `z_source_max` | 20 | 10 |
| `theta_e_min`, `theta_e_max` (arcsec) | 0.01, 60 | 0.12, 13 |
| `ellipticity_max` (per component) | 0.8 | 0.5 |
| `n_sersic_min`, `n_sersic_max` | 0.36, 8 | 0.36, 8 |
| `numpix_min`, `numpix_max` | 16, 4096 | 16, 1024 |
| `deltapix_min`, `deltapix_max` (arcsec) | 0.001, 1.0 | 0.01, 0.5 |
| `halo_mass_min`, `halo_mass_max` (M_sun) | not checked | 1e10, 1e14 |
| `axion_mass_min`, `axion_mass_max` (eV) | not checked | 1e-24, 1e-22 |
| `vortex_mass_min`, `vortex_mass_max` (M_sun) | not checked | 1e9, 1e12 |
| `snr_min`, `snr_max` (peak SNR) | not checked | 14, 60 |
| `snr_noise_excess` | not used | 1.35 |

## `general`

Sanity bounds for any galaxy- or cluster-scale simulation. They are there to
catch unit slips, typos and swapped values, not to judge unusual science.

- **Redshifts:** guards only. Lensed sources have been observed beyond z = 10.
- **Einstein radius:** from sub-arcsecond galaxy lenses to the tens of
  arcseconds of the largest cluster lenses.
- **Ellipticity:** 0.8 per component corresponds to an axis ratio near 0.1.
- **Sersic index:** below about 0.36 the profile is numerically invalid in
  lenstronomy; the upper bound is a guard.
- **Grid:** from milliarcsecond to ground-based pixel scales.

## `deeplense`

The bounds the DeepLense AI Scientist uses for the DeepLenseSim Model_I recipe
(<https://github.com/mwt5345/DeepLenseSim>). File references are to that
repository.

- **Redshifts:** guards. The recipe fixes the lens at z = 0.5 and the source at
  z = 1.0 (`deeplense/lens.py`, constructor defaults).
- **Einstein radius:** derived with the recipe's own `mass_to_radius`
  (`deeplense/lens.py:69-101`) at the recipe redshifts: halo masses of 1e10,
  1e12 and 1e14 M_sun give 0.128, 1.281 and 12.8 arcsec. The LensPop
  Euclid-discoverable population (Collett 2015) has theta_E of about
  0.66 +/- 0.40 arcsec, comfortably inside.
- **Ellipticity:** a guard keeping the axis ratio above about 1/3. The recipe
  fixes the lens at (0.1, 0) and the source at (-0.1, 0.1).
- **Grid:** spans the recipe's 150 and 64 pixel grids and its 0.05 arcsec
  pixels, as well as lenstronomy's HST (0.08), Euclid (0.101), LSST (0.2) and
  DES (0.263) pixel scales.
- **Masses:** the recipe fixes the halo at 1e12 M_sun and the vortex at 3e10
  M_sun, with bounds around them; it draws the axion mass as 10^U(-24, -22) eV,
  which the axion bounds match exactly.
- **Peak SNR:** measured on 900 Model_I images generated with the unmodified
  recipe: median 18.1, interquartile range 16.3-20.1, 5th percentile 14.8,
  95th percentile 22.0. The lower bound is the 5th percentile rounded down; the
  upper bound is a guard against a runaway source amplitude.
- **The SNR estimate:** lenstronomy's Sersic `amp` is the surface brightness
  at `R_sersic`, rising toward `amp * exp(b_n)` at the centre: about 5 times
  `amp` at n = 1 and 14 at n = 1.5. At n = 4 the cusp is so sharp that
  lenstronomy flattens it inside 0.001 arcsec, which still leaves the centre
  about 340 times `amp` for `R_sersic` = 0.3 arcsec (1.9.2). The estimate takes each
  source profile's centre, blurs it by the PSF and the pixel, and narrows that
  blur along the arc by the lens's tangential stretch (an SIS approximation),
  so no rendering is needed. A `GAUSSIAN` source's `amp` is its total flux.
  The noise is the recipe's, whose clipped background makes the image corners
  quieter than the arc.
- **`snr_noise_excess`:** how far the brightest pixel of a noisy image sits
  above the noiseless peak, in units of that pixel's noise. 1.35 makes the
  recipe's canonical parameters reproduce the measured median (18.1); its
  exposure and source-centre draws then give a 5th-95th percentile range of
  14.7-21.7 against the measured 14.8-22.0.

**Accuracy of the SNR estimate.** Against 500 lenstronomy 1.9.2 renders with
pixel scales of 0.03-0.2 arcsec, varied PSFs and backgrounds, and n_sersic
0.5-6, the median error stays within 2% up to n = 4.5. The scatter grows with
n, from within 10% below n = 1 to about 25% at n = 2-3, because a cusp smaller
than a pixel lands at a random offset from the pixel centres. The noise model
and its calibration are the recipe's, which is why the `general` preset does
not check SNR.

## References

- Birrer, S. & Amara, A. 2018, Physics of the Dark Universe, 22, 189.
- Collett, T. E. 2015, The Astrophysical Journal, 811, 20.
