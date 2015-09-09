import theano
import theano.tensor as T
import numpy as np
from theano_toolkit import utils as U
from theano_toolkit.parameters import Parameters
def initial_weights(input_size,output_size,factor=4):
    return np.asarray(
      np.random.uniform(
         low  = -factor * np.sqrt(6. / (input_size + output_size)),
         high =  factor * np.sqrt(6. / (input_size + output_size)),
         size =  (input_size,output_size)
      ),
      dtype=theano.config.floatX
    )

def relu(X):
    return ( X > 0 ) * X

def relu_init(input_size,output_size):
    return (np.random.randn(input_size,output_size) \
         * np.sqrt(2.0 / input_size)).astype(np.float32)

def build_classifier(
        P, name,
        input_sizes, hidden_sizes, output_size,
        initial_weights=initial_weights,
        activation=T.nnet.softplus):
    combine_inputs = build_combine_transform(
            P,"%s_input"%name,
            input_sizes,hidden_sizes[0],
            activation=activation
        )
    transforms = build_stacked_transforms(P,name,hidden_sizes,activation=activation)
    output = build_transform(
        P,"%s_output"%name,hidden_sizes[-1],output_size,
        initial_weights=lambda x,y:np.zeros((x,y)),
        activation=T.nnet.softmax
    )
    def classify(Xs):
        hidden_0 = combine_inputs(Xs)
        hiddens = transforms(hidden_0)
        return hiddens,output(hiddens[-1])
    return classify


def build_stacked_transforms(
        P,name,sizes,
        initial_weights=initial_weights,
        activation=T.nnet.softplus):
    if len(sizes) == 1:
        return lambda X:[X]
    else:
        transform_stack = build_stacked_transforms(
                P,name,sizes[:-1],
                initial_weights=initial_weights,
                activation=T.nnet.softplus,
            )
        transform = build_transform(
                P,"%s_%d"%(name,len(sizes)-1),
                sizes[-2],sizes[-1]
            )
        def t(X):
            layers = transform_stack(X)
            return layers + [transform(layers[-1])]
        return t

def build_transform(
        P,name,input_size,output_size,
        initial_weights=initial_weights,
        activation=T.nnet.softplus):
    P["W_%s"%name] = initial_weights(input_size,output_size)
    P["b_%s"%name] = np.zeros((output_size,), dtype=np.float32)
    W = P["W_%s"%name]
    b = P["b_%s"%name]
    def transform(X):
        output = activation(T.dot(X, W) + b)
        output.name = name
        return output
    return transform

def build_combine_transform(
        P,name,input_sizes,output_size,
        initial_weights=initial_weights,
        activation=T.nnet.softplus):
    weights = initial_weights(sum(input_sizes),output_size)

    Ws = []
    acc_size = 0
    for i,size in enumerate(input_sizes):
        P["W_%s_%d"%(name,i)] = weights[acc_size:acc_size+size]
        Ws.append(P["W_%s_%d"%(name,i)])
        acc_size += size
    P["b_%s"%name] = np.zeros((output_size,), dtype=np.float32)
    b = P["b_%s"%name]
    def transform(Xs):
        acc = 0.
        for X,W in zip(Xs,Ws):
            if X.dtype.startswith('int'):
                acc += W[X]
            else:
                acc += T.dot(X,W)
        return activation(acc + b)
    return transform

if __name__ == "__main__":
    import vae
    P = Parameters()
    inferer = build_classifier(P,"z1_latent",[10,5],[5,5,5,5],5)

    print inferer([
            T.constant(np.arange(5)),
            T.constant(np.eye(5,dtype=np.float32))
        ]).eval()
