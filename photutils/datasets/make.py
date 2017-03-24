# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Make example datasets.
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import numpy as np
from astropy.convolution import discretize_model
from astropy.io import fits
from astropy.modeling.models import Gaussian2D
from astropy.table import Table
from astropy.wcs import WCS

from ..utils import check_random_state


__all__ = ['apply_poisson_noise', 'make_noise_image',
           'make_gaussian_sources_image',
           'make_random_gaussians_table', 'make_4gaussians_image',
           'make_100gaussians_image', 'make_random_models_table',
           'make_model_sources_image', 'make_wcs', 'make_imagehdu']


def apply_poisson_noise(data, random_state=None):
    """
    Apply Poisson noise to an array, where the value of each element in
    the input array represents the expected number of counts.

    Each pixel in the output array is generated by drawing a random
    sample from a Poisson distribution whose expectation value is given
    by the pixel value in the input array.

    Parameters
    ----------
    data : array-like
        The array on which to apply Poisson noise.  Every pixel in the
        array must have a positive value (i.e. counts).

    random_state : int or `~numpy.random.RandomState`, optional
        Pseudo-random number generator state used for random sampling.

    Returns
    -------
    result : `~numpy.ndarray`
        The data array after applying Poisson noise.

    See Also
    --------
    make_noise_image

    Examples
    --------

    .. plot::
        :include-source:

        from photutils.datasets import make_4gaussians_image
        from photutils.datasets import apply_poisson_noise

        data1 = make_4gaussians_image(noise=False)
        data2 = apply_poisson_noise(data1, random_state=12345)

        # plot the images
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8))
        ax1.imshow(data1, origin='lower', interpolation='nearest')
        ax1.set_title('Original image')
        ax2.imshow(data2, origin='lower', interpolation='nearest')
        ax2.set_title('Original image with Poisson noise applied')
    """

    data = np.asanyarray(data)
    if np.any(data < 0):
        raise ValueError('data must not contain any negative values')

    prng = check_random_state(random_state)

    return prng.poisson(data)


def make_noise_image(image_shape, type='gaussian', mean=None, stddev=None,
                     random_state=None):
    """
    Make a noise image containing Gaussian or Poisson noise.

    Parameters
    ----------
    image_shape : 2-tuple of int
        Shape of the output 2D image.

    type : {'gaussian', 'poisson'}
        The distribution used to generate the random noise.

            * ``'gaussian'``: Gaussian distributed noise.
            * ``'poisson'``: Poisson distributed noise.

    mean : float
        The mean of the random distribution.  Required for both Gaussian
        and Poisson noise.

    stddev : float, optional
        The standard deviation of the Gaussian noise to add to the
        output image.  Required for Gaussian noise and ignored for
        Poisson noise (the variance of the Poisson distribution is equal
        to its mean).

    random_state : int or `~numpy.random.RandomState`, optional
        Pseudo-random number generator state used for random sampling.
        Separate function calls with the same noise parameters and
        ``random_state`` will generate the identical noise image.

    Returns
    -------
    image : `~numpy.ndarray`
        Image containing random noise.

    See Also
    --------
    apply_poisson_noise

    Examples
    --------

    .. plot::
        :include-source:

        # make a Gaussian and Poisson noise image
        from photutils.datasets import make_noise_image
        shape = (100, 100)
        image1 = make_noise_image(shape, type='gaussian', mean=0., stddev=5.)
        image2 = make_noise_image(shape, type='poisson', mean=5.)

        # plot the images
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 4))
        ax1.imshow(image1, origin='lower', interpolation='nearest')
        ax1.set_title('Gaussian noise ($\\mu=0$, $\\sigma=5.$)')
        ax2.imshow(image2, origin='lower', interpolation='nearest')
        ax2.set_title('Poisson noise ($\\mu=5$)')
    """

    if mean is None:
        raise ValueError('"mean" must be input')
    prng = check_random_state(random_state)
    if type == 'gaussian':
        if stddev is None:
            raise ValueError('"stddev" must be input for Gaussian noise')
        image = prng.normal(loc=mean, scale=stddev, size=image_shape)
    elif type == 'poisson':
        image = prng.poisson(lam=mean, size=image_shape)
    else:
        raise ValueError('Invalid type: {0}. Use one of '
                         '{"gaussian", "poisson"}.'.format(type))

    return image


def make_gaussian_sources_image(image_shape, source_table, oversample=1):
    """
    Make an image containing 2D Gaussian sources.

    Parameters
    ----------
    image_shape : 2-tuple of int
        Shape of the output 2D image.

    source_table : `~astropy.table.Table`
        Table of parameters for the Gaussian sources.  Each row of the
        table corresponds to a Gaussian source whose parameters are
        defined by the column names.  The column names must include
        ``flux`` or ``amplitude``, ``x_mean``, ``y_mean``, ``x_stddev``,
        ``y_stddev``, and ``theta`` (see
        `~astropy.modeling.functional_models.Gaussian2D` for a
        description of most of these parameter names).  If both ``flux``
        and ``amplitude`` are present, then ``amplitude`` will be
        ignored.

    oversample : float, optional
        The sampling factor used to discretize the
        `~astropy.modeling.functional_models.Gaussian2D` models on a
        pixel grid.

        If the value is 1.0 (the default), then the models will be
        discretized by taking the value at the center of the pixel bin.
        Note that this method will not preserve the total flux of very
        small sources.

        Otherwise, the models will be discretized by taking the average
        over an oversampled grid.  The pixels will be oversampled by the
        ``oversample`` factor.

    Returns
    -------
    image : `~numpy.ndarray`
        Image containing 2D Gaussian sources.

    See Also
    --------
    make_random_gaussians_table, make_noise_image, apply_poisson_noise

    Examples
    --------

    .. plot::
        :include-source:

        # make a table of Gaussian sources
        from astropy.table import Table
        table = Table()
        table['amplitude'] = [50, 70, 150, 210]
        table['x_mean'] = [160, 25, 150, 90]
        table['y_mean'] = [70, 40, 25, 60]
        table['x_stddev'] = [15.2, 5.1, 3., 8.1]
        table['y_stddev'] = [2.6, 2.5, 3., 4.7]
        table['theta'] = np.array([145., 20., 0., 60.]) * np.pi / 180.

        # make an image of the sources without noise, with Gaussian
        # noise, and with Poisson noise
        from photutils.datasets import make_gaussian_sources_image
        from photutils.datasets import make_noise_image
        shape = (100, 200)
        image1 = make_gaussian_sources_image(shape, table)
        image2 = image1 + make_noise_image(shape, type='gaussian', mean=5.,
                                           stddev=5.)
        image3 = image1 + make_noise_image(shape, type='poisson', mean=5.)

        # plot the images
        import matplotlib.pyplot as plt
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(8, 12))
        ax1.imshow(image1, origin='lower', interpolation='nearest')
        ax2.imshow(image2, origin='lower', interpolation='nearest')
        ax3.imshow(image3, origin='lower', interpolation='nearest')
    """

    # TODO: change to *fail* if flux/amplitude are both present?
    if 'flux' in source_table.colnames:
        source_table = source_table.copy()
        amplitude = source_table['flux'] / (2. * np.pi *
                                            source_table['x_stddev'] *
                                            source_table['y_stddev'])
        source_table['amplitude'] = amplitude
        del source_table['flux']
    elif 'amplitude' not in source_table.colnames:
        raise ValueError('either "amplitude" or "flux" must be columns in '
                         'the input source_table')

    model = Gaussian2D(x_stddev=1, y_stddev=1)
    return make_model_sources_image(image_shape, model, source_table,
                                    oversample)


def make_model_sources_image(image_shape, model, source_table, oversample=1):
    """
    Make an image containing sources generated from a user-specified flux model.

    Parameters
    ----------
    image_shape : 2-tuple of int or `~numpy.ndarray`
        If a 2-tuple, shape of the output 2D image.  If an array, these sources
        will be *added* to that array.

    model : 2D astropy.modeling.models object
        The model to be used for rendering the sources.

    source_table : `~astropy.table.Table`
        Table of parameters for the sources.  The column names must
        match the model parameter names.  Column names that do not match
        model parameters will be ignored.  Any model parameter that is
        *not* in the table will be left at whatever value it has for
        ``model``.

    oversample : float, optional
        The sampling factor used to discretize the models on a
        pixel grid.

        If the value is 1.0 (the default), then the models will be
        discretized by taking the value at the center of the pixel bin.
        Note that this method will not preserve the total flux of very
        small sources.

        Otherwise, the models will be discretized by taking the average
        over an oversampled grid.  The pixels will be oversampled by the
        ``oversample`` factor.

    Returns
    -------
    image : `~numpy.ndarray`
        Image containing model sources.
    """

    image = np.zeros(image_shape, dtype=np.float64)
    y, x = np.indices(image_shape)

    params_to_set = []
    for colnm in source_table.colnames:
        if colnm in model.param_names:
            params_to_set.append(colnm)

    # use this to store the *initial* values so we can set them back when done
    # with the loop.  Best not to copy a model, because some PSF models may have
    # substantial amounts of data in them
    init_params = {pnm: getattr(model, pnm) for pnm in params_to_set}

    try:
        for i, source in enumerate(source_table):
            for paramnm in params_to_set:
                setattr(model, paramnm, source[paramnm])
            if oversample == 1:
                image += model(x, y)
            else:
                image += discretize_model(model, (0, image_shape[1]),
                                          (0, image_shape[0]), mode='oversample',
                                          factor=oversample)
    finally:
        for pnm, val in init_params.items():
            setattr(model, paramnm, val)

    return image


def make_random_gaussians_table(n_sources, flux_range, xmean_range,
                                ymean_range, xstddev_range, ystddev_range,
                                amplitude_range=None, random_state=None):
    """
    Make a `~astropy.table.Table` containing parameters for randomly
    generated 2D Gaussian sources.

    Each row of the table corresponds to a Gaussian source whose
    parameters are defined by the column names.  The parameters are
    drawn from a uniform distribution over the specified input bounds.

    The output table can be input into `make_gaussian_sources_image` to
    create an image containing the 2D Gaussian sources.

    Parameters
    ----------
    n_sources : float
        The number of random Gaussian sources to generate.

    flux_range : array-like
        The lower and upper boundaries, ``(lower, upper)``, of the
        uniform distribution from which to draw source fluxes.
        ``flux_range`` will be ignored if ``amplitude_range`` is input.

    xmean_range : array-like
        The lower and upper boundaries, ``(lower, upper)``, of the
        uniform distribution from which to draw source ``x_mean``.

    ymean_range : array-like
        The lower and upper boundaries, ``(lower, upper)``, of the
        uniform distribution from which to draw source ``y_mean``.

    xstddev_range : array-like
        The lower and upper boundaries, ``(lower, upper)``, of the
        uniform distribution from which to draw source ``x_stddev``.

    ystddev_range : array-like
        The lower and upper boundaries, ``(lower, upper)``, of the
        uniform distribution from which to draw source ``y_stddev``.

    amplitude_range : array-like, optional
        The lower and upper boundaries, ``(lower, upper)``, of the
        uniform distribution from which to draw source amplitudes.  If
        ``amplitude_range`` is input, then ``flux_range`` will be
        ignored.

    random_state : int or `~numpy.random.RandomState`, optional
        Pseudo-random number generator state used for random sampling.
        Separate function calls with the same parameters and
        ``random_state`` will generate the identical sources.

    Returns
    -------
    table : `~astropy.table.Table`
        A table of parameters for the randomly generated Gaussian
        sources.  Each row of the table corresponds to a Gaussian source
        whose parameters are defined by the column names.  The column
        names will include ``flux`` or ``amplitude``, ``x_mean``,
        ``y_mean``, ``x_stddev``, ``y_stddev``, and ``theta`` (see
        `~astropy.modeling.functional_models.Gaussian2D` for a
        description of most of these parameter names).

    See Also
    --------
    make_gaussian_sources_image, make_noise_image, apply_poisson_noise

    Examples
    --------

    .. plot::
        :include-source:

        # create the random sources
        from photutils.datasets import make_random_gaussians_table
        n_sources = 100
        flux_range = [500, 1000]
        xmean_range = [0, 500]
        ymean_range = [0, 300]
        xstddev_range = [1, 5]
        ystddev_range = [1, 5]
        table = make_random_gaussians_table(n_sources, flux_range,
                                            xmean_range, ymean_range,
                                            xstddev_range, ystddev_range,
                                            random_state=12345)

        # make an image of the random sources without noise, with
        # Gaussian noise, and with Poisson noise
        from photutils.datasets import make_gaussian_sources_image
        from photutils.datasets import make_noise_image
        shape = (300, 500)
        image1 = make_gaussian_sources_image(shape, table)
        image2 = image1 + make_noise_image(shape, type='gaussian', mean=5.,
                                           stddev=2.)
        image3 = image1 + make_noise_image(shape, type='poisson', mean=5.)

        # plot the images
        import matplotlib.pyplot as plt
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(8, 12))
        ax1.imshow(image1, origin='lower', interpolation='nearest')
        ax2.imshow(image2, origin='lower', interpolation='nearest')
        ax3.imshow(image3, origin='lower', interpolation='nearest')
    """

    prng = check_random_state(random_state)
    sources = Table()
    if amplitude_range is None:
        sources['flux'] = prng.uniform(flux_range[0], flux_range[1], n_sources)
    else:
        sources['amplitude'] = prng.uniform(amplitude_range[0],
                                            amplitude_range[1], n_sources)
    sources['x_mean'] = prng.uniform(xmean_range[0], xmean_range[1], n_sources)
    sources['y_mean'] = prng.uniform(ymean_range[0], ymean_range[1], n_sources)
    sources['x_stddev'] = prng.uniform(xstddev_range[0], xstddev_range[1],
                                       n_sources)
    sources['y_stddev'] = prng.uniform(ystddev_range[0], ystddev_range[1],
                                       n_sources)
    sources['theta'] = prng.uniform(0, 2.*np.pi, n_sources)
    return sources


def make_4gaussians_image(noise=True):
    """
    Make an example image containing four 2D Gaussians plus a constant
    background.

    The background has a mean of 5.

    If ``noise`` is `True`, then Gaussian noise with a standard
    deviation of 5 is added to the output image.

    Parameters
    ----------
    noise : bool, optional
        Whether to include noise in the output image (default is
        `True`).

    Returns
    -------
    image : `~numpy.ndarray`
        Image containing four 2D Gaussian sources.

    See Also
    --------
    make_100gaussians_image

    Examples
    --------
    .. plot::
        :include-source:

        from photutils import datasets
        image = datasets.make_4gaussians_image()
        plt.imshow(image, origin='lower', cmap='gray')
    """

    table = Table()
    table['amplitude'] = [50, 70, 150, 210]
    table['x_mean'] = [160, 25, 150, 90]
    table['y_mean'] = [70, 40, 25, 60]
    table['x_stddev'] = [15.2, 5.1, 3., 8.1]
    table['y_stddev'] = [2.6, 2.5, 3., 4.7]
    table['theta'] = np.array([145., 20., 0., 60.]) * np.pi / 180.
    shape = (100, 200)
    data = make_gaussian_sources_image(shape, table) + 5.

    if noise:
        data += make_noise_image(shape, type='gaussian', mean=0.,
                                 stddev=5., random_state=12345)

    return data


def make_100gaussians_image(noise=True):
    """
    Make an example image containing 100 2D Gaussians plus a constant
    background.

    The background has a mean of 5.

    If ``noise`` is `True`, then Gaussian noise with a standard
    deviation of 2 is added to the output image.

    Parameters
    ----------
    noise : bool, optional
        Whether to include noise in the output image (default is
        `True`).

    Returns
    -------
    image : `~numpy.ndarray`
        Image containing 100 2D Gaussian sources.

    See Also
    --------
    make_4gaussians_image

    Examples
    --------
    .. plot::
        :include-source:

        from photutils import datasets
        image = datasets.make_100gaussians_image()
        plt.imshow(image, origin='lower', cmap='gray')
    """

    n_sources = 100
    flux_range = [500, 1000]
    xmean_range = [0, 500]
    ymean_range = [0, 300]
    xstddev_range = [1, 5]
    ystddev_range = [1, 5]
    table = make_random_gaussians_table(n_sources, flux_range, xmean_range,
                                        ymean_range, xstddev_range,
                                        ystddev_range, random_state=12345)
    shape = (300, 500)
    data = make_gaussian_sources_image(shape, table) + 5.

    if noise:
        data += make_noise_image(shape, type='gaussian', mean=0.,
                                 stddev=2., random_state=12345)

    return data


def make_random_models_table(model, n_sources, param_ranges=None,
                             random_state=None):
    """
    Make an `~astropy.table.Table` and the actual image for a simulated set of
    sources encoded as a PSF or other astropy model.

    Parameters
    ----------
    model : 2D astropy.modeling.models object
        The model to be used for the sources.

    n_sources : int
        The number of random Gaussian sources to generate

    param_ranges : dict or None
        The lower and upper boundaries for each of the parameters in ``model``
        as a dict mapping the parameter name to a ``(lower, upper)``. Must be
        valid parameter names for ``model``.

    random_state : int or `~numpy.random.RandomState`, optional
        Pseudo-random number generator state used for random sampling.
        Separate function calls with the same parameters and
        ``random_state`` will generate identical sources.

    Returns
    -------
    table : `~astropy.table.Table`
        A table of parameters for the randomly generated Gaussian
        sources.  Each row of the table corresponds to a Gaussian source
        whose parameters are defined by the column names.  The column
        names will be the keys of the dictionary ``param_ranges``.
    """

    prng = check_random_state(random_state)

    sources = Table()

    for pnm, (lower, upper) in param_ranges.items():
        if pnm not in model.param_names:
            raise ValueError('Requested parameter {} is not in model {}'.format(pnm, model))
        sources[pnm] = prng.uniform(lower, upper, n_sources)

    return sources


def make_wcs(shape):
    """
    Create a simple celestial WCS object.

    Parameters
    ----------
    shape : 2-tuple of int
        The shape of the 2D array to be used with the output
        `~astropy.wcs.WCS` object.

    Returns
    -------
    wcs : `~astropy.wcs.WCS` object
        The world coordinate system (WCS) transformation.
    """

    wcs = WCS(naxis=2)
    rho = np.pi / 3.
    scale = 0.1 / 3600.
    wcs._naxis1 = shape[1]     # nx
    wcs._naxis2 = shape[0]     # ny
    wcs.wcs.crpix = [shape[1] / 2, shape[0] / 2]     # 1-indexed (x, y)
    wcs.wcs.crval = [197.8925, -1.36555556]
    wcs.wcs.cunit = ['deg', 'deg']
    wcs.wcs.radesys = 'ICRS'
    wcs.wcs.cd = [[-scale * np.cos(rho), scale * np.sin(rho)],
                  [scale * np.sin(rho), scale * np.cos(rho)]]
    wcs.wcs.ctype = ['RA---TAN', 'DEC--TAN']

    return wcs


def make_imagehdu(data, wcs=None):
    """
    Create a FITS `~astropy.io.fits.ImageHDU` containing the input 2D
    image.

    Parameters
    ----------
    data : 2D array-like
        The input 2D data.

    wcs : `~astropy.wcs.WCS`, optional
        The world coordinate system (WCS) transformation to include in
        the output FITS header.

    Returns
    -------
    image_hdu : `~astropy.io.fits.ImageHDU`
        The FITS `~astropy.io.fits.ImageHDU`.
    """

    data = np.asanyarray(data)
    if data.ndim != 2:
        raise ValueError('data must be a 2D array')

    if wcs is not None:
        header = wcs.to_header()
    else:
        header = None

    return fits.ImageHDU(data, header=header)
