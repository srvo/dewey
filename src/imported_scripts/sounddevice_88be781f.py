# Copyright (c) 2015-2023 Matthias Geier
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Play and Record Sound with Python.

API overview:
  * Convenience functions to play and record NumPy arrays:
    `play()`, `rec()`, `playrec()` and the related functions
    `wait()`, `stop()`, `get_status()`, `get_stream()`

  * Functions to get information about the available hardware:
    `query_devices()`, `query_hostapis()`,
    `check_input_settings()`, `check_output_settings()`

  * Module-wide default settings: `default`

  * Platform-specific settings:
    `AsioSettings`, `CoreAudioSettings`, `WasapiSettings`

  * PortAudio streams, using NumPy arrays:
    `Stream`, `InputStream`, `OutputStream`

  * PortAudio streams, using Python buffer objects (NumPy not needed):
    `RawStream`, `RawInputStream`, `RawOutputStream`

  * Miscellaneous functions and classes:
    `sleep()`, `get_portaudio_version()`, `CallbackFlags`,
    `CallbackStop`, `CallbackAbort`

Online documentation:
    https://python-sounddevice.readthedocs.io/

"""
__version__ = '0.5.1'

import atexit as _atexit
import os as _os
import platform as _platform
import sys as _sys
from ctypes.util import find_library as _find_library
from _sounddevice import ffi as _ffi


try:
    for _libname in (
            'portaudio',  # Default name on POSIX systems
            'bin\\libportaudio-2.dll',  # DLL from conda-forge
            'lib/libportaudio.dylib',  # dylib from anaconda
            ):
        _libname = _find_library(_libname)
        if _libname is not None:
            break
    else:
        raise OSError('PortAudio library not found')
    _lib = _ffi.dlopen(_libname)
except OSError:
    if _platform.system() == 'Darwin':
        _libname = 'libportaudio.dylib'
    elif _platform.system() == 'Windows':
        if 'SD_ENABLE_ASIO' in _os.environ:
            _libname = 'libportaudio' + _platform.architecture()[0] + '-asio.dll'
        else:
            _libname = 'libportaudio' + _platform.architecture()[0] + '.dll'
    else:
        raise
    import _sounddevice_data
    _libname = _os.path.join(
        next(iter(_sounddevice_data.__path__)), 'portaudio-binaries', _libname)
    _lib = _ffi.dlopen(_libname)

_sampleformats = {
    'float32': _lib.paFloat32,
    'int32': _lib.paInt32,
    'int24': _lib.paInt24,
    'int16': _lib.paInt16,
    'int8': _lib.paInt8,
    'uint8': _lib.paUInt8,
}

_initialized = 0
_last_callback = None


def play(data, samplerate=None, mapping=None, blocking=False, loop=False,
         **kwargs):
    """Play back a NumPy array containing audio data.

    This is a convenience function for interactive use and for small
    scripts.  It cannot be used for multiple overlapping playbacks.

    This function does the following steps internally:

    * Call `stop()` to terminate any currently running invocation
      of `play()`, `rec()` and `playrec()`.

    * Create an `OutputStream` and a callback function for taking care
      of the actual playback.

    * Start the stream.

    * If ``blocking=True`` was given, wait until playback is done.
      If not, return immediately
      (to start waiting at a later point, `wait()` can be used).

    If you need more control (e.g. block-wise gapless playback, multiple
    overlapping playbacks, ...), you should explicitly create an
    `OutputStream` yourself.
    If NumPy is not available, you can use a `RawOutputStream`.

    Parameters
    ----------
    data : array_like
        Audio data to be played back.  The columns of a two-dimensional
        array are interpreted as channels, one-dimensional arrays are
        treated as mono data.
        The data types *float64*, *float32*, *int32*, *int16*, *int8*
        and *uint8* can be used.
        *float64* data is simply converted to *float32* before passing
        it to PortAudio, because it's not supported natively.
    mapping : array_like, optional
        List of channel numbers (starting with 1) where the columns of
        *data* shall be played back on.  Must have the same length as
        number of channels in *data* (except if *data* is mono, in which
        case the signal is played back on all given output channels).
        Each channel number may only appear once in *mapping*.
    blocking : bool, optional
        If ``False`` (the default), return immediately (but playback
        continues in the background), if ``True``, wait until playback
        is finished.  A non-blocking invocation can be stopped with
        `stop()` or turned into a blocking one with `wait()`.
    loop : bool, optional
        Play *data* in a loop.

    Other Parameters
    ----------------
    samplerate, **kwargs
        All parameters of `OutputStream` -- except *channels*, *dtype*,
        *callback* and *finished_callback* -- can be used.

    Notes
    -----
    If you don't specify the correct sampling rate
    (either with the *samplerate* argument or by assigning a value to
    `default.samplerate`), the audio data will be played back,
    but it might be too slow or too fast!

    See Also
    --------
    rec, playrec

    """
    ctx = _CallbackContext(loop=loop)
    ctx.frames = ctx.check_data(data, mapping, kwargs.get('device'))

    def callback(outdata, frames, time, status):
        assert len(outdata) == frames
        ctx.callback_enter(status, outdata)
        ctx.write_outdata(outdata)
        ctx.callback_exit()

    ctx.start_stream(OutputStream, samplerate, ctx.output_channels,
                     ctx.output_dtype, callback, blocking,
                     prime_output_buffers_using_stream_callback=False,
                     **kwargs)


def rec(frames=None, samplerate=None, channels=None, dtype=None,
        out=None, mapping=None, blocking=False, **kwargs):
    """Record audio data into a NumPy array.

    This is a convenience function for interactive use and for small
    scripts.

    This function does the following steps internally:

    * Call `stop()` to terminate any currently running invocation
      of `play()`, `rec()` and `playrec()`.

    * Create an `InputStream` and a callback function for taking care
      of the actual recording.

    * Start the stream.

    * If ``blocking=True`` was given, wait until recording is done.
      If not, return immediately
      (to start waiting at a later point, `wait()` can be used).

    If you need more control (e.g. block-wise gapless recording,
    overlapping recordings, ...), you should explicitly create an
    `InputStream` yourself.
    If NumPy is not available, you can use a `RawInputStream`.

    Parameters
    ----------
    frames : int, sometimes optional
        Number of frames to record.  Not needed if *out* is given.
    channels : int, optional
        Number of channels to record.  Not needed if *mapping* or *out*
        is given.  The default value can be changed with
        `default.channels`.
    dtype : str or numpy.dtype, optional
        Data type of the recording.  Not needed if *out* is given.
        The data types *float64*, *float32*, *int32*, *int16*, *int8*
        and *uint8* can be used.  For ``dtype='float64'``, audio data is
        recorded in *float32* format and converted afterwards, because
        it's not natively supported by PortAudio.  The default value can
        be changed with `default.dtype`.
    mapping : array_like, optional
        List of channel numbers (starting with 1) to record.
        If *mapping* is given, *channels* is silently ignored.
    blocking : bool, optional
        If ``False`` (the default), return immediately (but recording
        continues in the background), if ``True``, wait until recording
        is finished.
        A non-blocking invocation can be stopped with `stop()` or turned
        into a blocking one with `wait()`.

    Returns
    -------
    numpy.ndarray or type(out)
        The recorded data.

        .. note:: By default (``blocking=False``), an array of data is
           returned which is still being written to while recording!
           The returned data is only valid once recording has stopped.
           Use `wait()` to make sure the recording is finished.

    Other Parameters
    ----------------
    out : numpy.ndarray or subclass, optional
        If *out* is specified, the recorded data is written into the
        given array instead of creating a new array.
        In this case, the arguments *frames*, *channels* and *dtype* are
        silently ignored!
        If *mapping* is given, its length must match the number of
        channels in *out*.
    samplerate, **kwargs
        All parameters of `InputStream` -- except *callback* and
        *finished_callback* -- can be used.

    Notes
    -----
    If you don't specify a sampling rate (either with the *samplerate*
    argument or by assigning a value to `default.samplerate`),
    the default sampling rate of the sound device will be used
    (see `query_devices()`).

    See Also
    --------
    play, playrec

    """
    ctx = _CallbackContext()
    out, ctx.frames = ctx.check_out(out, frames, channels, dtype, mapping)

    def callback(indata, frames, time, status):
        assert len(indata) == frames
        ctx.callback_enter(status, indata)
        ctx.read_indata(indata)
        ctx.callback_exit()

    ctx.start_stream(InputStream, samplerate, ctx.input_channels,
                     ctx.input_dtype, callback, blocking, **kwargs)
    return out


def playrec(data, samplerate=None, channels=None, dtype=None,
            out=None, input_mapping=None, output_mapping=None, blocking=False,
            **kwargs):
    """Simultaneous playback and recording of NumPy arrays.

    This function does the following steps internally:

    * Call `stop()` to terminate any currently running invocation
      of `play()`, `rec()` and `playrec()`.

    * Create a `Stream` and a callback function for taking care of the
      actual playback and recording.

    * Start the stream.

    * If ``blocking=True`` was given, wait until playback/recording is
      done.  If not, return immediately
      (to start waiting at a later point, `wait()` can be used).

    If you need more control (e.g. block-wise gapless playback and
    recording, realtime processing, ...),
    you should explicitly create a `Stream` yourself.
    If NumPy is not available, you can use a `RawStream`.

    Parameters
    ----------
    data : array_like
        Audio data to be played back.  See `play()`.
    channels : int, sometimes optional
        Number of input channels, see `rec()`.
        The number of output channels is obtained from *data.shape*.
    dtype : str or numpy.dtype, optional
        Input data type, see `rec()`.
        If *dtype* is not specified, it is taken from *data.dtype*
        (i.e. `default.dtype` is ignored).
        The output data type is obtained from *data.dtype* anyway.
    input_mapping, output_mapping : array_like, optional
        See the parameter *mapping* of `rec()` and `play()`,
        respectively.
    blocking : bool, optional
        If ``False`` (the default), return immediately (but continue
        playback/recording in the background), if ``True``, wait until
        playback/recording is finished.
        A non-blocking invocation can be stopped with `stop()` or turned
        into a blocking one with `wait()`.

    Returns
    -------
    numpy.ndarray or type(out)
        The recorded data.  See `rec()`.

    Other Parameters
    ----------------
    out : numpy.ndarray or subclass, optional
        See `rec()`.
    samplerate, **kwargs
        All parameters of `Stream` -- except *channels*, *dtype*,
        *callback* and *finished_callback* -- can be used.

    Notes
    -----
    If you don't specify the correct sampling rate
    (either with the *samplerate* argument or by assigning a value to
    `default.samplerate`), the audio data will be played back,
    but it might be too slow or too fast!

    See Also
    --------
    play, rec

    """
    ctx = _CallbackContext()
    output_frames = ctx.check_data(data, output_mapping, kwargs.get('device'))
    if dtype is None:
        dtype = ctx.data.dtype  # ignore module defaults
    out, input_frames = ctx.check_out(out, output_frames, channels, dtype,
                                      input_mapping)
    if input_frames != output_frames:
        raise ValueError('len(data) != len(out)')
    ctx.frames = input_frames

    def callback(indata, outdata, frames, time, status):
        assert len(indata) == len(outdata) == frames
        ctx.callback_enter(status, indata)
        ctx.read_indata(indata)
        ctx.write_outdata(outdata)
        ctx.callback_exit()

    ctx.start_stream(Stream, samplerate,
                     (ctx.input_channels, ctx.output_channels),
                     (ctx.input_dtype, ctx.output_dtype),
                     callback, blocking,
                     prime_output_buffers_using_stream_callback=False,
                     **kwargs)
    return out


def wait(ignore_errors=True):
    """Wait for `play()`/`rec()`/`playrec()` to be finished.

    Playback/recording can be stopped with a `KeyboardInterrupt`.

    Returns
    -------
    CallbackFlags or None
        If at least one buffer over-/underrun happened during the last
        playback/recording, a `CallbackFlags` object is returned.

    See Also
    --------
    get_status

    """
    if _last_callback:
        return _last_callback.wait(ignore_errors)


def stop(ignore_errors=True):
    """Stop playback/recording.

    This only stops `play()`, `rec()` and `playrec()`, but has no
    influence on streams created with `Stream`, `InputStream`,
    `OutputStream`, `RawStream`, `RawInputStream`, `RawOutputStream`.

    """
    if _last_callback:
        # Calling stop() before close() is necessary for older PortAudio
        # versions, see issue #87:
        _last_callback.stream.stop(ignore_errors)
        _last_callback.stream.close(ignore_errors)


def get_status():
    """Get info about over-/underflows in `play()`/`rec()`/`playrec()`.

    Returns
    -------
    CallbackFlags
        A `CallbackFlags` object that holds information about the last
        invocation of `play()`, `rec()` or `playrec()`.

    See Also
    --------
    wait

    """
    if _last_callback:
        return _last_callback.status
    else:
        raise RuntimeError('play()/rec()/playrec() was not called yet')


def get_stream():
    """Get a reference to the current stream.

    This applies only to streams created by calls to `play()`, `rec()`
    or `playrec()`.

    Returns
    -------
    Stream
        An `OutputStream`, `InputStream` or `Stream` associated with
        the last invocation of `play()`, `rec()` or `playrec()`,
        respectively.

    """
    if _last_callback:
        return _last_callback.stream
    else:
        raise RuntimeError('play()/rec()/playrec() was not called yet')


def query_devices(device=None, kind=None):
    """Return information about available devices.

    Information and capabilities of PortAudio devices.
    Devices may support input, output or both input and output.

    To find the default input/output device(s), use `default.device`.

    Parameters
    ----------
    device : int or str, optional
        Numeric device ID or device name substring(s).
        If specified, information about only the given *device* is
        returned in a single dictionary.
    kind : {'input', 'output'}, optional
        If *device* is not specified and *kind* is ``'input'`` or
        ``'output'``, a single dictionary is returned with information
        about the default input or output device, respectively.

    Returns
    -------
    dict or DeviceList
        A dictionary with information about the given *device* or -- if
        no arguments were specified -- a `DeviceList` containing one
        dictionary for each available device.
        The dictionaries have the following keys:

        ``'name'``
            The name of the device.
        ``'index'``
            The device index.
        ``'hostapi'``
            The ID of the corresponding host API.  Use
            `query_hostapis()` to get information about a host API.
        ``'max_input_channels'``, ``'max_output_channels'``
            The maximum number of input/output channels supported by the
            device.  See `default.channels`.
        ``'default_low_input_latency'``, ``'default_low_output_latency'``
            Default latency values for interactive performance.
            This is used if `default.latency` (or the *latency* argument
            of `playrec()`, `Stream` etc.) is set to ``'low'``.
        ``'default_high_input_latency'``, ``'default_high_output_latency'``
            Default latency values for robust non-interactive
            applications (e.g. playing sound files).
            This is used if `default.latency` (or the *latency* argument
            of `playrec()`, `Stream` etc.) is set to ``'high'``.
        ``'default_samplerate'``
            The default sampling frequency of the device.
            This is used if `default.samplerate` is not set.

    Notes
    -----
    The list of devices can also be displayed in a terminal:

    .. code-block:: sh

        python3 -m sounddevice

    Examples
    --------
    The returned `DeviceList` can be indexed and iterated over like any
    sequence type (yielding the abovementioned dictionaries), but it
    also has a special string representation which is shown when used in
    an interactive Python session.

    Each available device is listed on one line together with the
    corresponding device ID, which can be assigned to `default.device`
    or used as *device* argument in `play()`, `Stream` etc.

    The first character of a line is ``>`` for the default input device,
    ``<`` for the default output device and ``*`` for the default
    input/output device.  After the device ID and the device name, the
    corresponding host API name is displayed.  In the end of each line,
    the maximum number of input and output channels is shown.

    On a GNU/Linux computer it might look somewhat like this:

    >>> import sounddevice as sd
    >>> sd.query_devices()
       0 HDA Intel: ALC662 rev1 Analog (hw:0,0), ALSA (2 in, 2 out)
       1 HDA Intel: ALC662 rev1 Digital (hw:0,1), ALSA (0 in, 2 out)
       2 HDA Intel: HDMI 0 (hw:0,3), ALSA (0 in, 8 out)
       3 sysdefault, ALSA (128 in, 128 out)
       4 front, ALSA (0 in, 2 out)
       5 surround40, ALSA (0 in, 2 out)
       6 surround51, ALSA (0 in, 2 out)
       7 surround71, ALSA (0 in, 2 out)
       8 iec958, ALSA (0 in, 2 out)
       9 spdif, ALSA (0 in, 2 out)
      10 hdmi, ALSA (0 in, 8 out)
    * 11 default, ALSA (128 in, 128 out)
      12 dmix, ALSA (0 in, 2 out)
      13 /dev/dsp, OSS (16 in, 16 out)

    Note that ALSA provides access to some "real" and some "virtual"
    devices.  The latter sometimes have a ridiculously high number of
    (virtual) inputs and outputs.

    On macOS, you might get something similar to this:

    >>> sd.query_devices()
      0 Built-in Line Input, Core Audio (2 in, 0 out)
    > 1 Built-in Digital Input, Core Audio (2 in, 0 out)
    < 2 Built-in Output, Core Audio (0 in, 2 out)
      3 Built-in Line Output, Core Audio (0 in, 2 out)
      4 Built-in Digital Output, Core Audio (0 in, 2 out)

    """
    if kind not in ('input', 'output', None):
        raise ValueError(f'Invalid kind: {kind!r}')
    if device is None and kind is None:
        return DeviceList(query_devices(i)
                          for i in range(_check(_lib.Pa_GetDeviceCount())))
    device = _get_device_id(device, kind, raise_on_error=True)
    info = _lib.Pa_GetDeviceInfo(device)
    if not info:
        raise PortAudioError(f'Error querying device {device}')
    assert info.structVersion == 2
    name_bytes = _ffi.string(info.name)
    try:
        # We don't know beforehand if DirectSound and MME device names use
        # 'utf-8' or 'mbcs' encoding.  Let's try 'utf-8' first, because it more
        # likely raises an exception on 'mbcs' data than vice versa, see also
        # https://github.com/spatialaudio/python-sounddevice/issues/72.
        name = name_bytes.decode('utf-8')
    except UnicodeDecodeError:
        api_idx = _lib.Pa_HostApiTypeIdToHostApiIndex
        if info.hostApi in (api_idx(_lib.paDirectSound), api_idx(_lib.paMME)):
            name = name_bytes.decode('mbcs')
        elif info.hostApi == api_idx(_lib.paASIO):
            # See https://github.com/spatialaudio/python-sounddevice/issues/490
            import locale
            name = name_bytes.decode(locale.getpreferredencoding())
        else:
            raise
    device_dict = {
        'name': name,
        'index': device,
        'hostapi': info.hostApi,
        'max_input_channels': info.maxInputChannels,
        'max_output_channels': info.maxOutputChannels,
        'default_low_input_latency': info.defaultLowInputLatency,
        'default_low_output_latency': info.defaultLowOutputLatency,
        'default_high_input_latency': info.defaultHighInputLatency,
        'default_high_output_latency': info.defaultHighOutputLatency,
        'default_samplerate': info.defaultSampleRate,
    }
    if kind and device_dict['max_' + kind + '_channels'] < 1:
        raise ValueError(
            'Not an {} device: {!r}'.format(kind, device_dict['name']))
    return device_dict


def query_hostapis(index=None):
    """Return information about available host APIs.

    Parameters
    ----------
    index : int, optional
        If specified, information about only the given host API *index*
        is returned in a single dictionary.

    Returns
    -------
    dict or tuple of dict
        A dictionary with information about the given host API *index*
        or -- if no *index* was specified -- a tuple containing one
        dictionary for each available host API.
        The dictionaries have the following keys:

        ``'name'``
            The name of the host API.
        ``'devices'``
            A list of device IDs belonging to the host API.
            Use `query_devices()` to get information about a device.
        ``'default_input_device'``, ``'default_output_device'``
            The device ID of the default input/output device of the host
            API.  If no default input/output device exists for the given
            host API, this is -1.

            .. note:: The overall default device(s) -- which can be
                overwritten by assigning to `default.device` -- take(s)
                precedence over `default.hostapi` and the information in
                the abovementioned dictionaries.

    See Also
    --------
    query_devices

    """
    if index is None:
        return tuple(query_hostapis(i)
                     for i in range(_check(_lib.Pa_GetHostApiCount())))
    info = _lib.Pa_GetHostApiInfo(index)
    if not info:
        raise PortAudioError(f'Error querying host API {index}')
    assert info.structVersion == 1
    return {
        'name': _ffi.string(info.name).decode(),
        'devices': [_lib.Pa_HostApiDeviceIndexToDeviceIndex(index, i)
                    for i in range(info.deviceCount)],
        'default_input_device': info.defaultInputDevice,
        'default_output_device': info.defaultOutputDevice,
    }


def check_input_settings(device=None, channels=None, dtype=None,
                         extra_settings=None, samplerate=None):
    """Check if given input device settings are supported.

    All parameters are optional, `default` settings are used for any
    unspecified parameters.  If the settings are supported, the function
    does nothing; if not, an exception is raised.

    Parameters
    ----------
    device : int or str, optional
        Device ID or device name substring(s), see `default.device`.
    channels : int, optional
        Number of input channels, see `default.channels`.
    dtype : str or numpy.dtype, optional
        Data type for input samples, see `default.dtype`.
    extra_settings : settings object, optional
        This can be used for host-API-specific input settings.
        See `default.extra_settings`.
    samplerate : float, optional
        Sampling frequency, see `default.samplerate`.

    """
    parameters, dtype, samplesize, samplerate = _get_stream_parameters(
        'input', device=device, channels=channels, dtype=dtype, latency=None,
        extra_settings=extra_settings, samplerate=samplerate)
    _check(_lib.Pa_IsFormatSupported(parameters, _ffi.NULL, samplerate))


def check_output_settings(device=None, channels=None, dtype=None,
                          extra_settings=None, samplerate=None):
    """Check if given output device settings are supported.

    Same as `check_input_settings()`, just for output device
    settings.

    """
    parameters, dtype, samplesize, samplerate = _get_stream_parameters(
        'output', device=device, channels=channels, dtype=dtype, latency=None,
        extra_settings=extra_settings, samplerate=samplerate)
    _check(_lib.Pa_IsFormatSupported(_ffi.NULL, parameters, samplerate))


def sleep(msec):
    """Put the caller to sleep for at least *msec* milliseconds.

    The function may sleep longer than requested so don't rely on this
    for accurate musical timing.

    """
    _lib.Pa_Sleep(msec)


def get_portaudio_version():
    """Get version information for the PortAudio library.

    Returns the release number and a textual description of the current
    PortAudio build, e.g. ::

        (1899, 'PortAudio V19-devel (built Feb 15 2014 23:28:00)')

    """
    return _lib.Pa_GetVersion(), _ffi.string(_lib.Pa_GetVersionText()).decode()


class _StreamBase:
    """Direct or indirect base class for all stream classes."""

    def __init__(self, kind, samplerate=None, blocksize=None, device=None,
                 channels=None, dtype=None, latency=None, extra_settings=None,
                 callback=None, finished_callback=None, clip_off=None,
                 dither_off=None, never_drop_input=None,
                 prime_output_buffers_using_stream_callback=None,
                 userdata=None, wrap_callback=None):
        """Base class for PortAudio streams.

        This class should only be used by library authors who want to
        create their own custom stream classes.
        Most users should use the derived classes
        `Stream`, `InputStream`, `OutputStream`,
        `RawStream`, `RawInputStream` and `RawOutputStream` instead.

        This class has the same properties and methods as `Stream`,
        except for `read_available`/:meth:`~Stream.read` and
        `write_available`/:meth:`~Stream.write`.

        It can be created with the same parameters as `Stream`,
        except that there are three additional parameters
        and the *callback* parameter also accepts a C function pointer.

        Parameters
        ----------
        kind : {'input', 'output', 'duplex'}
            The desired type of stream: for recording, playback or both.
        callback : Python callable or CData function pointer, optional
            If *wrap_callback* is ``None`` this can be a function pointer
            provided by CFFI.
            Otherwise, it has to be a Python callable.
        wrap_callback : {'array', 'buffer'}, optional
            If *callback* is a Python callable, this selects whether
            the audio data is provided as NumPy array (like in `Stream`)
            or as Python buffer object (like in `RawStream`).
        userdata : CData void pointer
            This is passed to the underlying C callback function
            on each call and can only be accessed from a *callback*
            provided as ``CData`` function pointer.

        Examples
        --------
        A usage example of this class can be seen at
        https://github.com/spatialaudio/python-rtmixer.

        """
        assert kind in ('input', 'output', 'duplex')
        assert wrap_callback in ('array', 'buffer', None)
        if wrap_callback == 'array':
            # Import NumPy as early as possible, see:
            # https://github.com/spatialaudio/python-sounddevice/issues/487
            import numpy
            assert numpy  # avoid "imported but unused" message (W0611)

        if blocksize is None:
            blocksize = default.blocksize
        if clip_off is None:
            clip_off = default.clip_off
        if dither_off is None:
            dither_off = default.dither_off
        if never_drop_input is None:
            never_drop_input = default.never_drop_input
        if prime_output_buffers_using_stream_callback is None:
            prime_output_buffers_using_stream_callback = \
                default.prime_output_buffers_using_stream_callback

        stream_flags = _lib.paNoFlag
        if clip_off:
            stream_flags |= _lib.paClipOff
        if dither_off:
            stream_flags |= _lib.paDitherOff
        if never_drop_input:
            stream_flags |= _lib.paNeverDropInput
        if prime_output_buffers_using_stream_callback:
            stream_flags |= _lib.paPrimeOutputBuffersUsingStreamCallback

        if kind == 'duplex':
            idevice, odevice = _split(device)
            ichannels, ochannels = _split(channels)
            idtype, odtype = _split(dtype)
            ilatency, olatency = _split(latency)
            iextra, oextra = _split(extra_settings)
            iparameters, idtype, isize, isamplerate = _get_stream_parameters(
                'input', idevice, ichannels, idtype, ilatency, iextra,
                samplerate)
            oparameters, odtype, osize, osamplerate = _get_stream_parameters(
                'output', odevice, ochannels, odtype, olatency, oextra,
                samplerate)
            self._dtype = idtype, odtype
            self._device = iparameters.device, oparameters.device
            self._channels = iparameters.channelCount, oparameters.channelCount
            self._samplesize = isize, osize
            if isamplerate != osamplerate:
                raise ValueError(
                    'Input and output device must have the same samplerate')
            else:
                samplerate = isamplerate
        else:
            parameters, self._dtype, self._samplesize, samplerate = \
                _get_stream_parameters(kind, device, channels, dtype, latency,
                                       extra_settings, samplerate)
            self._device = parameters.device
            self._channels = parameters.channelCount
            if kind == 'input':
                iparameters = parameters
                oparameters = _ffi.NULL
            elif kind == 'output':
                iparameters = _ffi.NULL
                oparameters = parameters

        ffi_callback = _ffi.callback('PaStreamCallback', error=_lib.paAbort)

        if callback is None:
            callback_ptr = _ffi.NULL
        elif kind == 'input' and wrap_callback == 'buffer':

            @ffi_callback
            def callback_ptr(iptr, optr, frames, time, status, _):
                data = _buffer(iptr, frames, self._channels, self._samplesize)
                return _wrap_callback(callback, data, frames, time, status)

        elif kind == 'input' and wrap_callback == 'array':

            @ffi_callback
            def callback_ptr(iptr, optr, frames, time, status, _):
                data = _array(
                    _buffer(iptr, frames, self._channels, self._samplesize),
                    self._channels, self._dtype)
                return _wrap_callback(callback, data, frames, time, status)

        elif kind == 'output' and wrap_callback == 'buffer':

            @ffi_callback
            def callback_ptr(iptr, optr, frames, time, status, _):
                data = _buffer(optr, frames, self._channels, self._samplesize)
                return _wrap_callback(callback, data, frames, time, status)

        elif kind == 'output' and wrap_callback == 'array':

            @ffi_callback
            def callback_ptr(iptr, optr, frames, time, status, _):
                data = _array(
                    _buffer(optr, frames, self._channels, self._samplesize),
                    self._channels, self._dtype)
                return _wrap_callback(callback, data, frames, time, status)

        elif kind == 'duplex' and wrap_callback == 'buffer':

            @ffi_callback
            def callback_ptr(iptr, optr, frames, time, status, _):
                ichannels, ochannels = self._channels
                isize, osize = self._samplesize
                idata = _buffer(iptr, frames, ichannels, isize)
                odata = _buffer(optr, frames, ochannels, osize)
                return _wrap_callback(
                    callback, idata, odata, frames, time, status)

        elif kind == 'duplex' and wrap_callback == 'array':

            @ffi_callback
            def callback_ptr(iptr, optr, frames, time, status, _):
                ichannels, ochannels = self._channels
                idtype, odtype = self._dtype
                isize, osize = self._samplesize
                idata = _array(_buffer(iptr, frames, ichannels, isize),
                               ichannels, idtype)
                odata = _array(_buffer(optr, frames, ochannels, osize),
                               ochannels, odtype)
                return _wrap_callback(
                    callback, idata, odata, frames, time, status)

        else:
            # Use cast() to allow CData from different FFI instance:
            callback_ptr = _ffi.cast('PaStreamCallback*', callback)

        # CFFI callback object must be kept alive during stream lifetime:
        self._callback = callback_ptr
        if userdata is None:
            userdata = _ffi.NULL
        self._ptr = _ffi.new('PaStream**')
        _check(_lib.Pa_OpenStream(self._ptr, iparameters, oparameters,
                                  samplerate, blocksize, stream_flags,
                                  callback_ptr, userdata),
               f'Error opening {self.__class__.__name__}')

        # dereference PaStream** --> PaStream*
        self._ptr = self._ptr[0]

        self._blocksize = blocksize
        info = _lib.Pa_GetStreamInfo(self._ptr)
        if not info:
            raise PortAudioError('Could not obtain stream info')
        # TODO: assert info.structVersion == 1
        self._samplerate = info.sampleRate
        if not oparameters:
            self._latency = info.inputLatency
        elif not iparameters:
            self._latency = info.outputLatency
        else:
            self._latency = info.inputLatency, info.outputLatency

        if finished_callback:
            if isinstance(finished_callback, _ffi.CData):
                self._finished_callback = finished_callback
            else:

                def finished_callback_wrapper(_):
                    return finished_callback()

                # CFFI callback object is kept alive during stream lifetime:
                self._finished_callback = _ffi.callback(
                    'PaStreamFinishedCallback', finished_callback_wrapper)
            _check(_lib.Pa_SetStreamFinishedCallback(self._ptr,
                                                     self._finished_callback))

    # Avoid confusion if something goes wrong before assigning self._ptr:
    _ptr = _ffi.NULL

    @property
    def samplerate(self):
        """The sampling frequency in Hertz (= frames per second).

        In cases where the hardware sampling frequency is inaccurate and
        PortAudio is aware of it, the value of this field may be
        different from the *samplerate* parameter passed to `Stream()`.
        If information about the actual hardware sampling frequency is
        not available, this field will have the same value as the
        *samplerate* parameter passed to `Stream()`.

        """
        return self._samplerate

    @property
    def blocksize(self):
        """Number of frames per block.

        The special value 0 means that the blocksize can change between
        blocks.  See the *blocksize* argument of `Stream`.

        """
        return self._blocksize

    @property
    def device(self):
        """IDs of the input/output device."""
        return self._device

    @property
    def channels(self):
        """The number of input/output channels."""
        return self._channels

    @property
    def dtype(self):
        """Data type of the audio samples.

        See Also
        --------
        default.dtype, samplesize

        """
        return self._dtype

    @property
    def samplesize(self):
        """The size in bytes of a single sample.

        See Also
        --------
        dtype

        """
        return self._samplesize

    @property
    def latency(self):
        """The input/output latency of the stream in seconds.

        This value provides the most accurate estimate of input/output
        latency available to the implementation.
        It may differ significantly from the *latency* value(s) passed
        to `Stream()`.

        """
        return self._latency

    @property
    def active(self):
        """``True`` when the stream is active, ``False`` otherwise.

        A stream is active after a successful call to `start()`, until
        it becomes inactive either as a result of a call to `stop()` or
        `abort()`, or as a result of an exception raised in the stream
        callback.  In the latter case, the stream is considered inactive
        after the last buffer has finished playing.

        See Also
        --------
        stopped

        """
        if self.closed:
            return False
        return _check(_lib.Pa_IsStreamActive(self._ptr)) == 1

    @property
    def stopped(self):
        """``True`` when the stream is stopped, ``False`` otherwise.

        A stream is considered to be stopped prior to a successful call
        to `start()` and after a successful call to `stop()` or
        `abort()`.  If a stream callback is cancelled (by raising an
        exception) the stream is *not* considered to be stopped.

        See Also
        --------
        active

        """
        if self.closed:
            return True
        return _check(_lib.Pa_IsStreamStopped(self._ptr)) == 1

    @property
    def closed(self):
        """``True`` after a call to `close()`, ``False`` otherwise."""
        return self._ptr == _ffi.NULL

    @property
    def time(self):
        """The current stream time in seconds.

        This is according to the same clock used to generate the
        timestamps passed with the *time* argument to the stream
        callback (see the *callback* argument of `Stream`).
        The time values are monotonically increasing and have
        unspecified origin.

        This provides valid time values for the entire life of the
        stream, from when the stream is opened until it is closed.
        Starting and stopping the stream does not affect the passage of
        time as provided here.

        This time may be used for synchronizing other events to the
        audio stream, for example synchronizing audio to MIDI.

        """
        time = _lib.Pa_GetStreamTime(self._ptr)
        if not time:
            raise PortAudioError('Error getting stream time')
        return time

    @property
    def cpu_load(self):
        """CPU usage information for the stream.

        The "CPU Load" is a fraction of total CPU time consumed by a
        callback stream's audio processing routines including, but not
        limited to the client supplied stream callback. This function
        does not work with blocking read/write streams.

        This may be used in the stream callback function or in the
        application.
        It provides a floating point value, typically between 0.0 and
        1.0, where 1.0 indicates that the stream callback is consuming
        the maximum number of CPU cycles possible to maintain real-time
        operation.  A value of 0.5 would imply that PortAudio and the
        stream callback was consuming roughly 50% of the available CPU
        time.  The value may exceed 1.0.  A value of 0.0 will always be
        returned for a blocking read/write stream, or if an error
        occurs.

        """
        return _lib.Pa_GetStreamCpuLoad(self._ptr)

    def __enter__(self):
        """Start  the stream in the beginning of a "with" statement."""
        self.start()
        return self

    def __exit__(self, *args):
        """Stop and close the stream when exiting a "with" statement."""
        self.stop()
        self.close()

    def start(self):
        """Commence audio processing.

        See Also
        --------
        stop, abort

        """
        err = _lib.Pa_StartStream(self._ptr)
        if err != _lib.paStreamIsNotStopped:
            _check(err, 'Error starting stream')

    def stop(self, ignore_errors=True):
        """Terminate audio processing.

        This waits until all pending audio buffers have been played
        before it returns.

        See Also
        --------
        start, abort

        """
        err = _lib.Pa_StopStream(self._ptr)
        if not ignore_errors:
            _check(err, 'Error stopping stream')

    def abort(self, ignore_errors=True):
        """Terminate audio processing immediately.

        This does not wait for pending buffers to complete.

        See Also
        --------
        start, stop

        """
        err = _lib.Pa_AbortStream(self._ptr)
        if not ignore_errors:
            _check(err, 'Error aborting stream')

    def close(self, ignore_errors=True):
        """Close the stream.

        If the audio stream is active any pending buffers are discarded
        as if `abort()` had been called.

        """
        err = _lib.Pa_CloseStream(self._ptr)
        self._ptr = _ffi.NULL
        if not ignore_errors:
            _check(err, 'Error closing stream')


class RawInputStream(_StreamBase):
    """Raw stream for recording only.  See __init__() and RawStream."""

    def __init__(self, samplerate=None, blocksize=None,
                 device=None, channels=None, dtype=None, latency=None,
                 extra_settings=None, callback=None, finished_callback=None,
                 clip_off=None, dither_off=None, never_drop_input=None,
                 prime_output_buffers_using_stream_callback=None):
        """PortAudio input stream (using buffer objects).

        This is the same as `InputStream`, except that the *callback*
        function and :meth:`~RawStream.read` work on plain Python buffer
        objects instead of on NumPy arrays.
        NumPy is not necessary for using this.

        Parameters
        ----------
        dtype : str
            See `RawStream`.
        callback : callable
            User-supplied function to consume audio data in response to
            requests from an active stream.
            The callback must have this signature:

            .. code-block:: text

                callback(indata: buffer, frames: int,
                         time: CData, status: CallbackFlags) -> None

            The arguments are the same as in the *callback* parameter of
            `RawStream`, except that *outdata* is missing.

        See Also
        --------
        RawStream, Stream

        """
        _StreamBase.__init__(self, kind='input', wrap_callback='buffer',
                             **_remove_self(locals()))

    @property
    def read_available(self):
        """The number of frames that can be read without waiting.

        Returns a value representing the maximum number of frames that
        can be read from the stream without blocking or busy waiting.

        """
        return _check(_lib.Pa_GetStreamReadAvailable(self._ptr))

    def read(self, frames):
        """Read samples from the stream into a buffer.

        This is the same as `Stream.read()`, except that it returns
        a plain Python buffer object instead of a NumPy array.
        NumPy is not necessary for using this.

        Parameters
        ----------
        frames : int
            The number of frames to be read.  See `Stream.read()`.

        Returns
        -------
        data : buffer
            A buffer of interleaved samples. The buffer contains
            samples in the format specified by the *dtype* parameter
            used to open the stream, and the number of channels
            specified by *channels*.
            See also `samplesize`.
        overflowed : bool
            See `Stream.read()`.

        """
        channels, _ = _split(self._channels)
        samplesize, _ = _split(self._samplesize)
        data = _ffi.new('signed char[]', channels * samplesize * frames)
        err = _lib.Pa_ReadStream(self._ptr, data, frames)
        if err == _lib.paInputOverflowed:
            overflowed = True
        else:
            _check(err)
            overflowed = False
        return _ffi.buffer(data), overflowed


class RawOutputStream(_StreamBase):
    """Raw stream for playback only.  See __init__() and RawStream."""

    def __init__(self, samplerate=None, blocksize=None,
                 device=None, channels=None, dtype=None, latency=None,
                 extra_settings=None, callback=None, finished_callback=None,
                 clip_off=None, dither_off=None, never_drop_input=None,
                 prime_output_buffers_using_stream_callback=None):
        """PortAudio output stream (using buffer objects).

        This is the same as `OutputStream`, except that the *callback*
        function and :meth:`~RawStream.write` work on plain Python
        buffer objects instead of on NumPy arrays.
        NumPy is not necessary for using this.

        Parameters
        ----------
        dtype : str
            See `RawStream`.
        callback : callable
            User-supplied function to generate audio data in response to
            requests from an active stream.
            The callback must have this signature:

            .. code-block:: text

                callback(outdata: buffer, frames: int,
                         time: CData, status: CallbackFlags) -> None

            The arguments are the same as in the *callback* parameter of
            `RawStream`, except that *indata* is missing.

        See Also
        --------
        RawStream, Stream

        """
        _StreamBase.__init__(self, kind='output', wrap_callback='buffer',
                             **_remove_self(locals()))

    @property
    def write_available(self):
        """The number of frames that can be written without waiting.

        Returns a value representing the maximum number of frames that
        can be written to the stream without blocking or busy waiting.

        """
        return _check(_lib.Pa_GetStreamWriteAvailable(self._ptr))

    def write(self, data):
        """Write samples to the stream.

        This is the same as `Stream.write()`, except that it expects
        a plain Python buffer object instead of a NumPy array.
        NumPy is not necessary for using this.

        Parameters
        ----------
        data : buffer or bytes or iterable of int
            A buffer of interleaved samples.  The buffer contains
            samples in the format specified by the *dtype* argument used
            to open the stream, and the number of channels specified by
            *channels*.  The length of the buffer is not constrained to
            a specific range, however high performance applications will
            want to match this parameter to the *blocksize* parameter
            used when opening the stream.  See also `samplesize`.

        Returns
        -------
        underflowed : bool
            See `Stream.write()`.

        """
        try:
            data = _ffi.from_buffer(data)
        except AttributeError:
            pass  # from_buffer() not supported
        except TypeError:
            pass  # input is not a buffer
        _, samplesize = _split(self._samplesize)
        _, channels = _split(self._channels)
        samples, remainder = divmod(len(data), samplesize)
        if remainder:
            raise ValueError('len(data) not divisible by samplesize')
        frames, remainder = divmod(samples, channels)
        if remainder:
            raise ValueError('Number of samples not divisible by channels')
        err = _lib.Pa_WriteStream(self._ptr, data, frames)
        if err == _lib.paOutputUnderflowed:
            underflowed = True
        else:
            _check(err)
            underflowed = False
        return underflowed


class RawStream(RawInputStream, RawOutputStream):
    """Raw stream for playback and recording.  See __init__()."""

    def __init__(self, samplerate=None, blocksize=None,
                 device=None, channels=None, dtype=None, latency=None,
