
import math
import numpy as np
np.set_printoptions(threshold=1000)

from dot import *
from pim import *

##############################################

class Network:
    def __init__(self, arrays, array_maps):
        self.arrays = arrays
        self.array_maps = array_maps
        self.num_layers = len(array_maps)

    def forward(self, x):
        num_examples, _, _, _ = np.shape(x)
        
        y = [None] * num_examples
        for example in range(num_examples):
            y[example] = x[example]
            for layer in range(self.num_layers):
                y[example] = self.conv(layer=layer, x=y[example])
                
        return y
        
    def conv(self, layer, x):
        '''
        Hi, Wi, Ci = np.shape(x)
        Fh, Fw, Fc, Co = np.shape(f)
        assert (Ci == Fc)
        Ho = conv_output_length(Hi, Fh, 'same', stride)
        Wo = conv_output_length(Hi, Fw, 'same', stride)

        x = np.pad(array=x, pad_width=[[pad1,pad2], [pad1,pad2], [0,0]], mode='constant')
        y = np.zeros(shape=(Ho, Wo, Co))
        f_matrix = np.reshape(f, (Fh * Fw * Ci, Co))

        for h in range(Ho):        
            for w in range(Wo):
                patch = np.reshape(x[h*stride:(h*stride+Fh), w*stride:(w*stride+Fw), :], -1)
                assert(np.prod(np.shape(patch)) == np.shape(f_matrix)[0])
                y[h, w, :] = dot(patch, f_matrix, b, q)
        '''
            
            
    def reduce(self):
        reduce_steps = np.log2(self.num_tiles)
        assert ((reduce_steps % 1) <= 0)
        reduce_steps = int(reduce_steps)
        
        for step in range(1, reduce_steps + 1):
            group = 2 ** step
            for tile in range(0, self.num_tiles, group):
                accum_tile = tile
                reduce_tile = tile + group // 2
                self.tiles[accum_tile].accum(self.tiles[reduce_tile].reduce())
                
        return self.tiles[0].reduce()
        
##############################################
'''
class Tile:
    def __init__(self, layers):
        self.layers = layers
        self.rec_count = 0
        self.send_count = 0
        self.y = 0

    def forward(self, layer, x):
        self.rec_count += np.prod(np.shape(x))
        self.y = self.layers[layer].forward(x)
        return self.y
                
    def reduce(self):
        self.send_count += np.prod(np.shape(self.y))
        return self.y
        
    def accum(self, x):
        self.rec_count += np.prod(np.shape(x))
        self.y += x
        return self.y
'''
##############################################

'''
array level design questions:
1) A) start with N arrays B) create a kernel and then figure out duplication 
2) A) init an array with list of weights B) or program them in.

> we are doing neither right now.
'''

class Array:
    def __init__(self, weights, params):
        self.weights = weights
        self.params = params
        self.shift = 2 ** np.array(range(self.params['bpw']))

    def dot(self, partition, x):
        # self.rec_count += np.prod(np.shape(x))
        y = self.weights[:, 0:len(x)] @ x
        y = np.reshape(y, (-1, self.params['bpw'])) @ self.shift
        return y

    '''
    def reduce(self):
        self.send_count += np.prod(np.shape(self.y))
        return self.y
        
    def accum(self, x):
        self.rec_count += np.prod(np.shape(x))
        self.y += x
        return self.y
    '''

##############################################

class Model:
    def __init__(self, layers):
        self.layers = layers
        
    def forward(self, x):
        num_examples, _, _, _ = np.shape(x)
        num_layers = len(self.layers)
        
        y = [None] * num_examples
        for example in range(num_examples):
            y[example] = x[example]
            for layer in range(num_layers):
                y[example] = self.layers[layer].forward(x=y[example])

        return y
        
    def forward_dist(self, x):
        num_examples, _, _, _ = np.shape(x)
        num_layers = len(self.layers)
        
        y = [None] * num_examples
        for example in range(num_examples):
            y[example] = x[example]
            for layer in range(num_layers):
                y[example] = self.layers[layer].forward_dist(x=y[example])

        return y

    def cut(self, params):
        num_layers = len(self.layers)

        arrays = []
        array_maps = []
        for layer in range(num_layers):
            weights = self.layers[layer].cut(params=params)
            nwl, _, nbl, _ = np.shape(weights)
            array_map = np.zeros(shape=(nwl, nbl, 2), dtype=np.int32) 
            for wl in range(nwl):
                for bl in range(nbl):
                    arrays.append(Array(weights=weights[wl, :, bl, :], params=params))
                    array_map[wl][bl] = np.array([len(arrays) - 1, 0])

            array_maps.append(array_map)
            
        for layer in range(num_layers):
            self.layers[layer].set_arrays(arrays)
            self.layers[layer].set_array_maps(array_maps[layer])
            
        return arrays, array_maps
                    
##############################################

class Layer:
    def __init__(self):
        assert(False)
        
    def forward(self, x):   
        assert(False)
        
    def rpr(self):
        assert(False)

    def cut(self, params):
        assert (False)
        
##############################################

class Conv(Layer):
    def __init__(self, input_size, filter_size, stride, pad1, pad2, weights):

        self.input_size = input_size
        self.h, self.w, self.c = self.input_size
                
        self.filter_size = filter_size
        self.fh, self.fw, self.fc, self.fn = self.filter_size
        
        assert(self.c == self.fc)
        assert(self.fh == self.fw)

        self.s = stride
        self.p1 = pad1
        self.p2 = pad2
        
        self.y_h = (self.h - self.fh + self.s + self.p1 + self.p2) / self.s
        self.y_w = (self.w - self.fw + self.s + self.p1 + self.p2) / self.s

        maxval = 2 ** (8 - 1)
        minval = -1 * maxval
        if weights is not None:
            self.w, self.b, self.q = weights
            assert (np.all(self.w >= minval))
            assert (np.all(self.w <= maxval))
            # check shape
            assert(np.shape(self.w) == self.filter_size)
            assert(np.shape(self.b) == (self.fn,))
            assert(np.shape(self.q) == ())
            # cast as int
            self.w = self.w.astype(int)
            self.b = self.b.astype(int)
            self.q = int(self.q)
            # q must be larger than 0
            assert(self.q > 0)
        else:
            values = np.array(range(minval + 1, maxval))
            self.w = np.random.choice(a=values, size=self.filter_size, replace=True).astype(int)
            self.b = np.zeros(shape=self.fn).astype(int)
            self.q = 200
        
    ##############################
        
    def set_arrays(self, arrays):
        self.arrays = arrays

    def set_array_maps(self, array_maps):
        self.array_maps = array_maps

    ##############################

    def forward(self, x):
        y = conv(x=x, f=self.w, b=self.b, q=self.q, stride=self.s, pad1=self.p1, pad2=self.p2)
        return y

    def forward_dist(self, x):
        Ho = conv_output_length(self.h, self.fh, 'same', self.s)
        Wo = Ho
        Co = self.fn

        x = np.pad(array=x, pad_width=[[self.p1,self.p2], [self.p1,self.p2], [0,0]], mode='constant')
        y = np.zeros(shape=(Ho, Wo, Co))

        for h in range(Ho):        
            for w in range(Wo):
                patch = np.reshape(x[h*self.s:(h*self.s+self.fh), w*self.s:(w*self.s+self.fw), :], -1)
                
                ah, aw, _ = np.shape(self.array_maps)
                for i in range(ah):
                    for j in range(aw):
                        x1 = i * 128
                        x2 = min(x1 + 128, len(patch))
                        
                        y1 = j * 16
                        y2 = y1 + 16
                                                
                        array, partition = self.array_maps[i][j]
                        y[h, w, y1:y2] = self.arrays[array].dot(partition, patch[x1:x2])
                        
        return y

    ##############################

    def cut(self, params):
        
        # nrow, nwl, wl, xb = np.shape(x)
        # nwl, wl, nbl, bl = np.shape(w) 
        # nrow, ncol = y_shape

        ########################

        w_offset = self.w + params['offset']
        w_matrix = np.reshape(w_offset, (self.fh * self.fw * self.fc, self.fn))
        wb = []
        for bit in range(params['bpw']):
            wb.append(np.bitwise_and(np.right_shift(w_matrix, bit), 1))
        wb = np.stack(wb, axis=-1)
        
        ########################
        
        nrow, ncol, nbit = np.shape(wb)
        if (nrow % params['rpa']):
            zeros = np.zeros(shape=(params['rpa'] - (nrow % params['rpa']), ncol, nbit))
            wb = np.concatenate((wb, zeros), axis=0)

        nrow, ncol, nbit = np.shape(wb)
        wb = np.reshape(wb, (-1, params['rpa'], ncol, nbit))
        
        ########################

        nwl, wl, ncol, nbit = np.shape(wb)
        wb = np.reshape(wb, (nwl, params['rpa'], ncol * nbit))
        
        nwl, wl, ncol = np.shape(wb)
        if (ncol % params['bl']):
            zeros = np.zeros(shape=(nwl, params['rpa'], params['bl'] - (ncol % params['bl'])))
            wb = np.concatenate((wb, zeros), axis=2)

        wb = np.reshape(wb, (nwl, params['rpa'], -1, params['bl']))

        ########################

        return wb
        
        

##############################################
        
        
        
        
        
        
        
        
