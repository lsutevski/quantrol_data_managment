from scipy.optimize import curve_fit
import numpy as np
from scipy.signal import find_peaks

APPEND_MODE = 1
OVERWRITE_MODE = 2

class data1D:
    def __init__(self, x=None, *args, **kwargs):
        self._x = np.array(x) if x is not None else np.array([])
        self._mode = kwargs.get('data_mode', OVERWRITE_MODE)

    def clear(self):
        self._x = np.array([])

    @property
    def x(self):
        return self._x
    
    @x.setter
    def x(self, array: np.ndarray | list):
        self._x = np.array(array)

    def poisson_process(self):
        raise NotImplementedError("Poisson process not implemented yet.")

class data2D:
    def __init__(self, x=None, y=None, t=None,*args, **kwargs):
        self._x = np.array(x) if x is not None else np.array([])
        self._y = np.array(y) if y is not None else np.array([])

        self._mode = kwargs.get('data_mode', OVERWRITE_MODE)
        self._quatratures = t == None or kwargs.get('quatratures', False)

    def clear(self):
        self.x = np.array([])
        self.y = np.array([])
    
    @property
    def x(self):
        if self._x.shape == self._y.shape:
            return self._x
        else:
            return np.array(range(self.y.shape[0]))

    @property
    def y(self):
        return self._y

    @x.setter
    def x(self, array: np.ndarray | list):
        if self._mode == APPEND_MODE:
            self._x = np.append(self._x, np.array(array))
        else:
            self._x = np.array(array)

    @y.setter
    def y(self, array: np.ndarray | list):
        if self._mode == APPEND_MODE:
            self._y = np.append(self._y, np.array(array))
        else:
            self._y = np.array(array)

    def fft(self):
        if self._x.size == 0 or self._y.size == 0:
            return np.array([]), np.array([])

        freqs = np.fft.fftfreq(self.x.size, d=(self.x[1] - self.x[0]))
        fft_values = np.fft.fft(self.y)
        indices = np.argsort(freqs)

        return freqs[indices], fft_values[indices]

    def derivative(self, x, y, order = 1):
        if x.size == 0 or y.size == 0:
            return np.array([]), np.array([])

        if order == 1:
            dy = np.gradient(y)
            dx = x[1] - x[0]
            return dy/dx
        
        else:
            return self.derivative(x, 
                                   self.derivative(x, y, order=order-1), 
                                   order=1)

    def fit_to(self, fitting_class):
        popt, fitting_func, pcov = fitting_class.fit(self.x, self.y)
        return popt, fitting_func, pcov


class data3D:
    def __init__(self, x=None, y=None, z=None):
        self.x = np.array(x) if x is not None else np.array([])
        self.y = np.array(y) if y is not None else np.array([])
        self.z = np.array(z) if z is not None else np.array([])

    def clear(self):
        self.x = np.array([])
        self.y = np.array([])
        self.z = np.array([])

    @property
    def x(self):
        if self.x.shape[0] == self.z.shape[1]:
            return self._x
        else:
            return np.array(range(self.z.shape[1]))

    @property
    def y(self):
        if self.y.shape[0] == self.z.shape[1]:
            return self._y
        else:
            return np.array(range(self.z.shape[0]))

    @property
    def z(self):
        return self._z

    @x.setter
    def x(self, array: np.ndarray | list):
        self._x = np.array(array)

    @y.setter
    def y(self, array: np.ndarray | list):
        self._y = np.array(array)

    @z.setter
    def z(self, array: np.ndarray | list):
        self._z = np.array(array)

    def fft(self):
        if self._x.size == 0 or self._y.size == 0 or self._z.size == 0:
            return np.array([]), np.array([]), np.array([])

        freqs = np.fft.fftfreq(self.x.size, d=(self.x[1] - self.x[0]))
        fft_values_y = np.fft.fft(self.y)
        fft_values_z = np.fft.fft(self.z)
        indices = np.argsort(freqs)

        return freqs[indices], fft_values_y[indices], fft_values_z[indices]

    def derivative(self, x, y, z, order = 1):
        if x.size == 0 or y.size == 0 or z.size == 0:
            return np.array([]), np.array([]), np.array([])

        if order == 1:
            dy = np.gradient(y)
            dz = np.gradient(z)
            dx = x[1] - x[0]
            return dy/dx, dz/dx

        else:
            return self.derivative(x,
                                   self.derivative(x, y, z, order=order-1),
                                   order=1)

    def fit_to(self, fitting_class):
        popt, fitting_func, pcov = fitting_class.fit(self.x, self.y, self.z)
        return fitting_func, popt, pcov


class Poly:
    '''
    Example of a fitting class and the methods involved.
    '''
    name = "polynomial"
    degree = 2
    maxfev = 1000

    @classmethod
    def get_params(cls):
        return {
            "degree": cls.degree,
            "maxfev": cls.maxfev
        }

    @classmethod
    def set_params(cls, **kwargs):
        for key, value in kwargs.items():
            if key in cls.__dict__:
                setattr(cls, key, value)

    @classmethod
    def give_estimate(cls, x, y):
        guess = [np.median(x)]
        for i in range(cls.degree + 1):
            guess.append(0)
        return guess

    @classmethod
    def fit(cls, x, y):
        popt, pcov = curve_fit(cls.poly_func, x, y, p0=cls.give_estimate(x, y))

        return popt, cls.poly_func, pcov
    
    @staticmethod
    def poly_func(x, *params):
        return sum(p * (x-params[0])**i for i, p in enumerate(params[1:]))

    @classmethod
    def name_parameters(cls):
        params = {
            0 : "b"
        }
        for i in range(1, cls.degree + 1):
            params[i] = f"a_{i}"

        return params

class Exponential:
    '''
    Example of a fitting class and the methods involved.
    '''
    name = "exponential"
    maxfev = 1000

    @classmethod
    def get_params(cls):
        return {
            "maxfev": cls.maxfev
        }

    @classmethod
    def set_params(cls, **kwargs):
        for key, value in kwargs.items():
            if key in cls.__dict__:
                setattr(cls, key, value)

    @classmethod
    def give_estimate(cls, x, y):
        offset = y[-1]
        a = (y[0] - offset)
        x0 = x[np.argmax(y)]

        return [a, x0, offset]

    @classmethod
    def fit(cls, x, y):
        popt, pcov = curve_fit(cls.exp_func, x, y, p0=cls.give_estimate(x, y))
        return popt, cls.exp_func, pcov

    @staticmethod
    def exp_func(x, a, x0, offset):
        return a * np.exp(- x / x0) + offset

    @classmethod
    def name_parameters(cls):
        return {
            0: "amplitude",
            1: "decay",
            2: "offset"
        }



class Cosine:
    '''
    Example of a fitting class and the methods involved.
    '''
    name = "sinusoidal"
    beating = False
    maxfev = 1000

    @classmethod
    def get_params(cls):
        return {
            "maxfev": cls.maxfev
        }

    @classmethod
    def set_params(cls, **kwargs):
        for key, value in kwargs.items():
            if key in cls.__dict__:
                setattr(cls, key, value)

    @classmethod
    def give_estimate(cls, x, y):
        offset = (np.max(y) + np.min(y)) / 2
        
        freqs = np.fft.fftfreq(x.size, d=(x[1] - x[0]))
        fft_values = np.fft.fft(y - offset)

        indices = np.argsort(freqs)

        freqs = freqs[indices]
        fft_values = fft_values[indices]

        positive_indices = np.where(freqs > 0)[0]
        freqs = freqs[positive_indices]
        fft_values = fft_values[positive_indices]

        if cls.beating:
            peaks, _ = find_peaks(fft_values, height=0)
            guess_freqs = freqs[peaks]  
            guess_phases = np.angle(fft_values[peaks])
            guess_amps = np.abs(fft_values[peaks])
        
        else:
            index = np.argmax(np.abs(fft_values))
            guess_freqs = np.abs(freqs[index])
            guess_phases = np.angle(fft_values[index])
            guess_amps = (np.max(y) - np.min(y)) / 2

        # plt.plot(freqs, np.abs(fft_values))
        print(guess_amps, guess_freqs, guess_phases, offset)

        return guess_amps, guess_freqs, guess_phases, offset

    @classmethod
    def fit(cls, x, y):
        popt, pcov = curve_fit(cls.cos_func, x, y, p0=cls.give_estimate(x, y))
        return popt, cls.cos_func, pcov

    @classmethod
    def cos_func(cls, x, a, f, phase, offset):
        if cls.beating:
            y = 0
            for i in range(a.shape[0]):
                y += a[i] * np.sin(2 * np.pi * f[i] * x  + phase[i])
            
            return y + offset
        else:
            return a * np.cos(2 * np.pi * f * x - phase) + offset

    @classmethod
    def name_parameters(cls):
        return {
            0: "amplitude",
            1: "period",
            2: "phase",
            3: "offset"
        }
