# https://github.com/tobydoig/3dword2vec/blob/master/w2v.py

import datetime
import pickle

import matplotlib.pyplot as plt
import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from umap import UMAP  # actually called "umap-learn"

from server.hipparchiaobjects.connectionobject import ConnectionObject


def log(msg):
    print(datetime.datetime.time(datetime.datetime.now()), msg)


# models tend to be quite large so we return a random sample of vectors
def sampleVectors(vectors, percentagetouse):
    size = len(vectors)
    log(f'Sampling {percentagetouse * 100}% of {size} vectors')
    sample = int(size * percentagetouse)
    totalfeatures = len(vectors[0])
    sampVecs = np.ndarray((sample, totalfeatures), np.float32)
    indices = np.random.choice(len(vectors), sample)
    for i, val in enumerate(indices):
        sampVecs[i] = vectors[val]
    return sampVecs, indices


def reduceWithPCA(vectors, size):
    log(f'Reducing data to {size} features using PCA (fast)')
    pca = PCA(n_components=size)
    vecs = pca.fit_transform(vectors)

    return vecs


def reduceWithUMAP(vectors, size):
    log(f'Reducing data to {size} features using UMAP (slow-ish)')
    umap = UMAP(n_neighbors=15, min_dist=0.1, metric='euclidean', n_components=size)
    vecs = umap.fit_transform(vectors)

    return vecs


def reduceWithTSNE(vectors, size):
    log(f'Reducing data to {size} features using T-SNE (slow)')
    tsne = TSNE(n_components=size)
    vecs = tsne.fit_transform(vectors)

    return vecs


def PCA_then_UMAP(vectors, pca_size, umap_size):
    pcaVecs = reduceWithPCA(vectors, pca_size)
    umapVecs = reduceWithUMAP(pcaVecs, umap_size)

    return umapVecs


def PCA_then_TSNE(vectors, pca_size, tsne_size):
    pcaVecs = reduceWithPCA(vectors, pca_size)
    tsneVecs = reduceWithTSNE(pcaVecs, tsne_size)

    return tsneVecs


def clusterForColour(vectors, size):
    log(f'Using KMeans to generate {size} groups so the final graph is prettier...')
    clusters = KMeans(n_clusters=size).fit_predict(vectors)

    return clusters


# save in a format our graphit.html file is expecting (basically a json object)
def saveAsGraphitFile(model, vectors, indices, clusters, fname):
    log(f'Writing data to {fname}...')
    f = open(fname, "w", encoding='utf-8')
    f.write('var W2VDATA=[\n')
    for i, val in enumerate(indices):
        kw = model.index2word[val]
        if len(kw) > 1:
            v = vectors[i]
            f.write('["')
            f.write(kw.replace('"', '\\"'))  # keyword
            f.write('",')
            f.write(str(v[0]))  # x
            f.write(',')
            f.write(str(v[1]))  # y
            f.write(',')
            f.write(str(v[2]))  # z
            f.write(',')
            f.write(str(clusters[i]))  # colour group (just an integer)
            f.write('],\n')
    f.write('];\n')
    f.close()

    return fname


def plot2D(vectors):
    x = np.flipud(np.rot90(vectors[:], k=1, axes=(0, 1)))
    plt.scatter(x[0], x[1], c=clusters, marker=".")
    plt.show()
    plt.pause(5)


q = """
select calculatedvectorspace
    from public.storedvectors 
    where uidlist=%s AND vectortype=%s limit 1;
"""

# Dio Chrysostomus (Soph.) [gr0612]
# seneca: lt1017
d = (['lt1017'], 'nn')

dbconnection = ConnectionObject()
cursor = dbconnection.cursor()
cursor.execute(q, d)
result = cursor.fetchone()

retreiveddata = pickle.loads(result[0])
gensimmodel = retreiveddata.wv
vectors, indices = sampleVectors(gensimmodel.vectors, 1.00)
vectors = PCA_then_UMAP(vectors, 50, 3)
clusters = clusterForColour(vectors, 10)
fname = saveAsGraphitFile(gensimmodel, vectors, indices, clusters, './html/keyword-data.js')

log(f'Finished, now open html/graphit.html')

# will eventually need:
# https://api.jquery.com/jQuery.getScript/
#   jQuery.getScript( url [, success ] )
#
# and cf https://stackoverflow.com/questions/5680657/adding-css-file-with-jquery#5680757
# $('head').append('<link rel="stylesheet" href="style2.css" type="text/css" />');

