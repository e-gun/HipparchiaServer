# https://github.com/tobydoig/3dword2vec/blob/master/w2v.py

import pickle
import gensim
import numpy as np
import zipfile
import datetime
import urllib.request
import os.path
import matplotlib.pyplot as plt
from umap import UMAP # actually called "umap-learn"
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.cluster import KMeans

from server.hipparchiaobjects.connectionobject import ConnectionObject

def log(msg):
    print(datetime.datetime.time(datetime.datetime.now()), msg)

# def downloadFile(url):
#     urllib.request.urlretrieve(url, './' + url.rpartition('/')[2])
#
# def unzip(zipname):
#     zip_ref = zipfile.ZipFile(zipname, 'r')
#     zip_ref.extractall('.')
#     zip_ref.close()

# google's word2vec model is binary and stored in a .gz which the gensim library can read directly, so no
# need to unzip.
# def downloadGoogleModel(url):
#     zipname = url.rpartition('/')[2]
#     if (not os.path.isfile(zipname)):
#         log(f'Downloading model from {url}')
#         downloadFile(url)
#     return zipname

# fasttext models come from https://fasttext.cc/docs/en/english-vectors.html
# they are text format and .zip encoded. the gensim library can't read these directly so need to unzip.
# def downloadFastTextModel(url):
#     zipname = url.rpartition('/')[2]
#     fname = zipname.rpartition('.')[0]
#
#     if (not os.path.isfile(fname)):
#         if (not os.path.isfile(zipname)):
#             log(f'Downloading model from {url}')
#             downloadFile(url)
#         log(f'Unzipping local model archive {zipname}')
#         unzip(zipname)
#
#     return fname

# Load the word2vec model off local disk, downloading if necessary.
# def loadModel(url):
#     fname = ''
#     if (url.endswith('.gz')):
#         fname = downloadGoogleModel(url)
#     else:
#         fname = downloadFastTextModel(url)
#
#     log(f'Loading local model {fname}')
#     model = gensim.models.KeyedVectors.load_word2vec_format('./' + fname, binary=fname.endswith('.gz'))
#
#     return model, fname

# models tend to be quite large so we return a random sample of vectors
def sampleVectors(vectors, size_frac):
    size = len(vectors)
    log(f'Sampling {size_frac * 100}% of {size} vectors')
    sample = int(size * size_frac)
    numFeat = len(vectors[0])
    sampVecs = np.ndarray((sample, numFeat), np.float32)
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


# # these are the word2vec pre-trained models we've tested against.
# MODELS = [
#     'https://s3.amazonaws.com/dl4j-distribution/GoogleNews-vectors-negative300.bin.gz',
#     'https://s3-us-west-1.amazonaws.com/fasttext-vectors/wiki-news-300d-1M.vec.zip',
#     'https://s3-us-west-1.amazonaws.com/fasttext-vectors/wiki-news-300d-1M-subword.vec.zip',
#     'https://s3-us-west-1.amazonaws.com/fasttext-vectors/crawl-300d-2M.vec.zip',
#     'https://s3-us-west-1.amazonaws.com/fasttext-vectors/crawl-300d-2M-subword.zip'
# ]

q = """
select calculatedvectorspace
    from public.storedvectors 
    where uidlist=%s AND vectortype=%s limit 1;
"""

d = (['lt1318'], 'nn')

dbconnection = ConnectionObject()
cursor = dbconnection.cursor()
cursor.execute(q, d)
result = cursor.fetchone()

# main
#url = MODELS[1]
#model, fname = loadModel(url)
m = pickle.loads(result[0])
model = m.wv
vectors, indices = sampleVectors(model.vectors, 0.60)
vectors = PCA_then_UMAP(vectors, 50, 3)
clusters = clusterForColour(vectors, 10)
fname = saveAsGraphitFile(model, vectors, indices, clusters, './html/keyword-data.js')

log(f'Finished, now open html/graphit.html')