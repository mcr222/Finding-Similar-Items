from __future__ import division
from nltk import ngrams
import md5
from sortedcontainers import SortedSet
import random
from sklearn.metrics import jaccard_similarity_score
import scipy.optimize as sp

'''
Hashes in text:
    Since documents are much shorter than 2^32 (32 bits hash combinations),
    we still can be sure that a document is only a small fraction of
    the possible tokens in it's sets.
'''
'''
Collision of hashes:
    There's a small chance of a collision where two shingles hashed to
    the same token, but that could make two documents appear to have shingles in common.
    
    But the number of different strings of length k=10 that will actually appear in
    any document is much smaller than 26^10 (26 alphabet characters) and also smaller 
    than 256^10 (256 ASCII characters).

'''        
        
def shingle_text(text, k):
    '''
    Takes a text and partitions it in hashed (4 byte hash) shingles of length k.
        @param text: string containing the text to shingle
        @param k: length of the characters in a shingle
        @return: ordered (by input order) set containing all hashes.
    '''
    shingled_text = SortedSet()
    #shingled by character (counting space as character too)
    kgram = ngrams(text,k)
    for gram in kgram:
        #hash the shingle into a token of 4 bytes (8 hexadecimal)
        shingled_text.add(int(md5.new(''.join(gram)).hexdigest()[0:8], 16))
    return shingled_text


def compareSets(set1,set2):
    '''
    Returns Jaccard similarity index between the two sets
        @param set1: first set
        @param set2: second set
    '''
    return float(len(set1 & set2)) / len(set1 | set2)

def compareSignatures(sig1,sig2):
    return jaccard_similarity_score(sig1, sig2);

def minHashing(allSets):

    #Union of all the hashes
    U = SortedSet()
    for i in range(0,len(allSets)):
        U |= allSets[i]

   #Generation of 100 hash functions
    totalFunctions = 100
    div = 1000000
    functions = []
    for i in range(0,totalFunctions):
        def func1(x):
            a = random.randint(1,1000)
            b = random.randint(1,1000)
            return (a*x +b)%div
        functions.append(func1)

   #Min hash algorithm
    'Initialization--------------------------------------------'
    M_i_c = [[float("inf")] * len(allSets) for i in range(totalFunctions)]
    i = 1

    for u in U:
        h_r = []
        #We calculate the hash functions for the specific row
        for h in range(0,len(functions)):
            result = functions[h](i)
            h_r.append(result)
        c_cont = 0
        #We iterate over the columns
        for c in allSets:
            if(c.__contains__(u)):
                for hh in range(0,len(functions)):
                    if(h_r[hh]<M_i_c[hh][c_cont]):
                        M_i_c[hh][c_cont] = h_r[hh]
            c_cont+=1
        i+=1

    print M_i_c

def LHS(signature_vectors, threshold):
    sign_length = len(signature_vectors[0])
    root_res = sp.root(lambda r: (r/sign_length)**(1/r)-threshold, 2)
    #beware that r might not divide exactly sign_length (last band might be smaller than r)
    r = int(root_res['x'][0])
    candidate_pairs = set()
    index = 0
    while index<sign_length:
        hash_buckets = np.full((2^32,1),-1)
        for doc in range(len(signature_vectors)):
            to_bucket = int(md5.new(''.join(gram)).hexdigest()[0:8], 16)
            if(hash_buckets[to_bucket]==-1):
                hash_buckets[to_bucket]=[doc]
            else:
                for doc_in_bucket in hash_buckets[to_bucket]:
                    #one might think that pairs of doc swapped can appear in the pairs, 
                    #meaning that we would have in the candidate_pairs (1,2) and (2,1)
                    #that's not possible cause we iterate from lower doc to bigger document
                    #thus cannot generate (2,1).
                    candidate_pairs.add((doc_in_bucket,doc))
                hash_buckets[to_bucket].append(doc)
                
    print candidate_pairs
    return candidate_pairs


def main():
    text1="try text"
    text2="hello text"
    k=3
    set1 = shingle_text(text1, k)
    print set1
    set2 = shingle_text(text2, k)
    print set2
    print compareSets(set1, set2)
    print compareSignatures([2,2,2], [2,4,2])
    minHashing([set1,set2])

    
main()