'''
#How to use a stateful LSTM model, stateful vs stateless LSTM performance comparison

[More documentation about the Keras LSTM model](/layers/recurrent/#lstm)

In this example, we train an LSTM to learn the moving average function.

The models are trained on an input/output pair, where
the input is a generated uniformly distributed
random sequence of length = `input_len`,
and the output is a moving average of the input with window length = `tsteps`.
Both `input_len` and `tsteps` are defined in the "editable parameters"
section.

A larger `tsteps` value means that the LSTM will need more memory
to figure out the input-output relationship.
This memory length is controlled by the `lahead` variable (more details below).

The rest of the parameters are:

- `input_len`: the length of the generated input sequence
- `lahead`: the input sequence length that the LSTM
  is trained on for each output point
- `batch_size`, `epochs`: same parameters as in the `model.fit(...)`
  function

When `lahead > 1`, the model input is preprocessed to a "rolling window view"
of the data, with the window length = `lahead`.
This is similar to sklearn's `view_as_windows`
with `window_shape` [being a single number.](
http://scikit-image.org/docs/0.10.x/api/skimage.util.html#view-as-windows)

When `lahead < tsteps`, only the stateful LSTM converges because its
statefulness allows it to see beyond the capability that lahead
gave it to fit the n-point average. The stateless LSTM does not have
this capability, and hence is limited by its `lahead` parameter,
which is not sufficient to see the n-point average.

When `lahead >= tsteps`, both the stateful and stateless LSTM converge.
Recommended values for tests:
lahead = 1, tsteps = 2 (stateless model does not converge)
lahead = 2, tsteps = 2 (stateless model converges)
lahead = 2, tsteps = 5 (stateless model does not converge)
lahead = 5, tsteps = 5 (stateless model converges)

This convergence can be seen by comparing the output values of the two sequences.
When the stateless LSTM does not converge, we see a larger error compared to the
stateful LSTM, and the values do not track the testing values well.

'''
from __future__ import print_function
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from keras.models import Sequential
from keras.layers import Dense, LSTM

# ---------------------------------------------
# EDITABLE PARAMETERS
# Read the documentation above for more details
# https://keras.io/examples/lstm_stateful/
# ---------------------------------------------

# length of input
input_len = 1000

# The window length of the moving average used to generate
# the output from the input in the input/output pair used
# to train the LSTM
# e.g. if tsteps=2 and input=[1, 2, 3, 4, 5],
#      then output=[1.5, 2.5, 3.5, 4.5]
tsteps = 2

# The input sequence length that the LSTM is trained on for each output point
lahead = 1

# training parameters passed to "model.fit(...)"
batch_size = 1
epochs = 10

# ------------
# MAIN PROGRAM
# ------------

print("*" * 33)
if lahead >= tsteps:
    print("STATELESS LSTM WILL ALSO CONVERGE")
else:
    print("STATELESS LSTM WILL NOT CONVERGE")
print("*" * 33)

np.random.seed(1986)

print('Generating Data...')


def gen_uniform_amp(amp=1, xn=10000):
    """Generates uniform random data between
    -amp and +amp
    and of length xn

    # Arguments
        amp: maximum/minimum range of uniform data
        xn: length of series
    """
    data_input = np.random.uniform(-1 * amp, +1 * amp, xn)
    data_input = pd.DataFrame(data_input)
    return data_input

# Since the output is a moving average of the input,
# the first few points of output will be NaN
# and will be dropped from the generated data
# before training the LSTM.
# Also, when lahead > 1,
# the preprocessing step later of "rolling window view"
# will also cause some points to be lost.
# For aesthetic reasons,
# in order to maintain generated data length = input_len after pre-processing,
# add a few points to account for the values that will be lost.
to_drop = max(tsteps - 1, lahead - 1)
data_input = gen_uniform_amp(amp=0.1, xn=input_len + to_drop)

# set the target to be a N-point average of the input
expected_output = data_input.rolling(window=tsteps, center=False).mean()

# when lahead > 1, need to convert the input to "rolling window view"
# https://docs.scipy.org/doc/numpy/reference/generated/numpy.repeat.html
if lahead > 1:
    data_input = np.repeat(data_input.values, repeats=lahead, axis=1)
    data_input = pd.DataFrame(data_input)
    for i, c in enumerate(data_input.columns):
        data_input[c] = data_input[c].shift(i)

# drop the nan
expected_output = expected_output[to_drop:]
data_input = data_input[to_drop:]

print('Input shape:', data_input.shape)
print('Output shape:', expected_output.shape)
print('Input head: ')
print(data_input.head())
print('Output head: ')
print(expected_output.head())
print('Input tail: ')
print(data_input.tail())
print('Output tail: ')
print(expected_output.tail())

print('Plotting input and expected output')
plt.plot(data_input[0][:10], '.')
plt.plot(expected_output[0][:10], '-')
plt.legend(['Input', 'Expected Output'])
plt.title('Input and Expected Output')
plt.show()


def create_model(stateful):
    model = Sequential()
    model.add(LSTM(20,
              input_shape=(lahead, 1),
              batch_size=batch_size,
              stateful=stateful))
    model.add(Dense(1))
    model.compile(loss='mse', optimizer='adam')
    return model


print('Creating Stateful Model...')
model_stateful = create_model(stateful=True)


# split train/test data
def split_data(x, y, ratio=0.8):
    to_train = int(input_len * ratio)
    # tweak to match with the batch_size
    to_train -= to_train % batch_size

    x_train = x[:to_train]
    y_train = y[:to_train]
    x_test = x[to_train:]
    y_test = y[to_train:]

    # tweak to match with batch_size
    to_drop = x.shape[0] % batch_size
    if to_drop > 0:
        x_test = x_test[:-1 * to_drop]
        y_test = y_test[:-1 * to_drop]

    # some reshaping
    reshape_3 = lambda x: x.values.reshape((x.shape[0], x.shape[1], 1))
    x_train = reshape_3(x_train)
    x_test = reshape_3(x_test)

    reshape_2 = lambda x: x.values.reshape((x.shape[0], 1))
    y_train = reshape_2(y_train)
    y_test = reshape_2(y_test)

    return (x_train, y_train), (x_test, y_test)


(x_train, y_train), (x_test, y_test) = split_data(data_input, expected_output)
print('x_train.shape: ', x_train.shape)
print('y_train.shape: ', y_train.shape)
print('x_test.shape: ', x_test.shape)
print('y_test.shape: ', y_test.shape)

print('Training')
for i in range(epochs):
    print('Epoch', i + 1, '/', epochs)
    # Note that the last state for sample i in a batch will
    # be used as initial state for sample i in the next batch.
    # Thus we are simultaneously training on batch_size series with
    # lower resolution than the original series contained in data_input.
    # Each of these series are offset by one step and can be
    # extracted with data_input[i::batch_size].
    model_stateful.fit(x_train,
                       y_train,
                       batch_size=batch_size,
                       # Using 5 epochs would give longer spread and also make the code faster
                       epochs=5,
                       verbose=1,
                       validation_data=(x_test, y_test),
                       shuffle=False)
    model_stateful.reset_states()

print('Predicting')
predicted_stateful = model_stateful.predict(x_test, batch_size=batch_size)

print('Creating Stateless Model...')
model_stateless = create_model(stateful=False)

print('Training')
model_stateless.fit(x_train,
                    y_train,
                    batch_size=batch_size,
                    epochs=epochs,
                    verbose=1,
                    validation_data=(x_test, y_test),
                    shuffle=False)

print('Predicting')
predicted_stateless = model_stateless.predict(x_test, batch_size=batch_size)


# ---------------------------------
# PLOTTING PREDICTIONS ON TEST DATA
# ---------------------------------
# Scale the y axis uniformly for all three plots.
# Find the largest value in all the prediction arrays,
# and scale that by 10%.
max_y = max(abs(np.concatenate([y_test, predicted_stateful,
                               predicted_stateless]))) * 1.1
min_y = max_y * -1

# Scale the x axis uniformly for all three plots using the length
# of the y_test array.
min_x = 0
max_x = len(y_test)

# Plot the expected and predicted values
plt.figure(figsize=(10, 10))
print('Plotting Expected and Predicted Values')
expected_plot = plt.subplot(3, 1, 1)
plt.plot(y_test)
plt.title('Y_Test (Moving Average)')
expected_plot.set_ylim([min_y, max_y])
expected_plot.set_xlim([min_x, max_x])
stateful_plot = plt.subplot(3, 1, 2)
# Note that the first "tsteps-1" in predicted_stateful are errors
# because it is not possible to predict them ((predicted_stateful).flatten()[:tsteps]).
plt.plot((predicted_stateful).flatten())
plt.title('Predicted: Stateful')
stateful_plot.set_ylim([min_y, max_y])
stateful_plot.set_xlim([min_x, max_x])
stateless_plot = plt.subplot(3, 1, 3)
plt.plot((predicted_stateless).flatten())
plt.title('Predicted: Stateless')
stateless_plot.set_ylim([min_y, max_y])
stateless_plot.set_xlim([min_x, max_x])
plt.show()

# Plot the errors between the expected and predicted values

# Calculate errors
y_test_err = y_test - y_test
predicted_stateful_err = y_test - predicted_stateful
predicted_stateless_err = y_test - predicted_stateless

# Calculate limits for y axis
max_err = max(abs(np.concatenate([y_test_err, predicted_stateful_err,
                                  predicted_stateless_err])))*1.1
#Since we are using EPOCH=5 so the min_eror= max_err * -5
min_err = max_err * -5

# Plot errors
plt.figure(figsize=(10, 10))
print('Plotting Errors between Y_Test and Predicted Values')
expected_err = plt.subplot(3, 1, 1)
plt.plot(y_test_err)
expected_err.set_ylim([min_err, max_err])
expected_err.set_xlim([min_x, max_x])
plt.title('Absolute Error in Y_Test: Y_Test - Y_Test')
stateful_err = plt.subplot(3, 1, 2)
plt.plot(predicted_stateful_err.flatten())
stateful_err.set_ylim([min_err, max_err])
stateful_err.set_xlim([min_x, max_x])
plt.title('Error in Stateful Predictions: Y_Test - predicted_stateless')
stateless_err = plt.subplot(3, 1, 3)
plt.plot((predicted_stateless_err).flatten())
stateless_err.set_ylim([min_err, max_err])
stateless_err.set_xlim([min_x, max_x])
plt.title('Error in Stateless Predictions: Y_Test - predicted_stateless')
plt.show()

