"""
Run scripts for individual models in Galaxy Zoo
"""
import time

import classes
import numpy as np
import logging
from constants import *
import models
from sklearn.cross_validation import KFold

logger = logging.getLogger('galaxy')


def train_set_average_benchmark(outfile="sub_average_benchmark_000.csv"):
    """
    What should be the actual baseline.  Takes the training set solutions, averages them, and uses that as the
    submission for every row in the test set
    """
    start_time = time.time()
    training_data = classes.TrainSolutions().data

    solutions = np.mean(training_data, axis=0)

    # Calculate an RMSE
    train_solution = np.tile(solutions, (N_TRAIN, 1))
    rmse = classes.rmse(train_solution, training_data)

    solution = classes.Submission(np.tile(solutions, (N_TEST, 1)))
    solution.to_file(outfile)

    end_time = time.time()
    logger.info("Model completed in {}".format(end_time - start_time))


def central_pixel_benchmark(outfile="sub_central_pixel_001.csv"):
    """
    Tries to duplicate the central pixel benchmark, which is defined as:
    Simple benchmark that clusters training galaxies according to the color in the center of the image
    and then assigns the associated probability values to like-colored images in the test set.
    """

    test_averages = models.Benchmarks.CentralPixelBenchmark().execute()
    predictions = classes.Submission(test_averages)
    # Write to file
    predictions.to_file(outfile)


def random_forest_001(outfile="sub_random_forest_001.csv", n_jobs=1):
    """
    First attempt at implementing a neural network.
    Uses a sample of central pixels in RGB space to feed in as inputs to the neural network

    # 3-fold CV using half the training set reports RMSE of .126 or so
    """
    model = models.RandomForest.RandomForestModel(n_jobs=n_jobs)
    model.run('train')
    predictions = model.run('predict')
    output = classes.Submission(predictions)
    output.to_file(outfile)


def extra_trees_test(n_jobs=1):
    """
    Exact same as random_forest_001, but using ExtraTreesRegressor to see if that method is any better
    """
    # model = models.RandomForest.ExtraTreesModel()
    # model.run('cv')

    # tune the model - 15 trees already gives .13 RMSE, I think that's slightly better than RF with that number of trees
    params = {
        'n_estimators': [15, 50, 100, 250]
    }
    model = models.RandomForest.ExtraTreesModel(
        grid_search_parameters=params,
        grid_search_sample=0.5,
        n_jobs=n_jobs
    )
    model.run('grid_search', refit=True)
    # 2014-01-21 05:45:28 - Base - INFO - Found best parameters:
    # 2014-01-21 05:45:28 - Base - INFO - {'n_estimators': 250}
    # 2014-01-21 05:45:28 - Base - INFO - Predicting on holdout set
    # 2014-01-21 05:45:41 - classes - INFO - RMSE: 0.124530683233
    # 2014-01-21 05:45:41 - Base - INFO - RMSE on holdout set: 0.124530683233
    # 2014-01-21 05:45:41 - Base - INFO - Grid search completed in 8916.21896791
    # 2014-01-21 05:45:41 - Base - INFO - Model completed in 9332.45440102

    # As expected, more trees = better performance.  Seems like the performance is on par/slightly better than random forest


def random_forest_cascade_001(outfile='sub_rf_cascade_001.csv'):
    """
    Experiment to compare whether training the random forest with all Ys or training the Ys in a cascade is better

    2014-01-22 10:19:39 - Base - INFO - Cross validation completed in 7038.78176308.  Scores:
    2014-01-22 10:19:39 - Base - INFO - [ 0.13103377  0.13196983]
    """
    mdl = models.RandomForest.RandomForestCascadeModel(cv_sample=0.1)
    mdl.run('cv')

    # Unscaled classes don't seem to work better than RF.  Lets try with scaled classes
    mdl_scaled = models.RandomForest.RandomForestCascadeModel(cv_sample=0.1, scaled=True)
    mdl_scaled.run('cv')


def ridge_rf_001(outfile='sub_ridge_rf_001.csv'):
    mdl = models.Ridge.RidgeRFModel(cv_sample=0.5, cv_folds=2)
    mdl.run('cv')
    mdl.run('train')
    mdl.run('predict')
    sub = classes.Submission(mdl.test_y)
    sub.to_file(outfile)


def unique_rows(data):
    """
    Returns the number of unique rows in a 2D NumPy array.
    Using it to check the number of duplicated clusters in K-Means learning
    @param data:
    @return:
    """
    data_set = set([tuple(row) for row in data])
    return len(data_set)


def svr_rf():
    # subsample
    train_y = classes.train_solutions.data

    # randomly sample 10% Y and select the gid's
    n = 7000
    crop_size = 150
    scale = 0.1
    train_y = train_y[np.random.randint(train_y.shape[0], size=n), :]
    train_x = np.zeros((n, (crop_size * scale) ** 2 * 3))

    # load the training images and crop at the same time
    for row, gid in enumerate(train_y[:, 0]):
        img = classes.RawImage(TRAIN_IMAGE_PATH + '/' + str(int(gid)) + '.jpg')
        img.crop(crop_size)
        img.rescale(scale)
        img.flatten()
        train_x[row] = img.data
        if (row % 10) == 0:
            print row


    parameters = {'alpha': [14], 'n_estimators': [10]}
    kf = KFold(train_x.shape[0], n_folds=2, shuffle=True)

    for train, test in kf:
        ridge_rf = models.SVR.SVRRFModel()
        ridge_rf.fit(train_x[train, :], train_y[train, :])
        res = ridge_rf.predict(train_x[test, :])
        classes.rmse(train_y[test, :], res)

    # transform images

    # cv and training


def kmeans_ridge_rf():
    km = models.KMeansFeatures.KMeansFeatures(rf_size=6, num_centroids=100, num_patches=400000)
    km.fit()
    n = 7000

    train_x = km.transform(n)
    train_y = classes.train_solutions.data[0:n, :]

    kf = KFold(n, n_folds=2, shuffle=True)

    for train, test in kf:
        clf = models.Ridge.RidgeRFEstimator()
        clf.fit(train_x[train], train_y[train])
        res = clf.predict(train_x[test])
        classes.rmse(train_y[test], res)

kmeans_ridge_rf()