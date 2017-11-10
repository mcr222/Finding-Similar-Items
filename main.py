from nltk import ngrams
import md5
from sortedcontainers import SortedSet
import random
from sklearn.metrics import jaccard_similarity_score
import scipy.optimize as sp
import numpy as np
        
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
        #hash the shingle with md5 into a token of 4 bytes (8 hexadecimal)
        #all the combinations of 8 hex characters are all the possible shingle hashes
        shingled_text.add(int(md5.new(''.join(gram)).hexdigest()[0:8], 16))
    return shingled_text


def compareSets(set1,set2):
    '''
    Returns Jaccard similarity index between the two sets
        @param set1: first set
        @param set2: second set
        @return: ratio of items in the intersection of the sets vs all distinct items in both sets
    '''
    return float(len(set1 & set2)) / len(set1 | set2)

def compareSignatures(sig1,sig2):
    '''
    Compares two arrays of integers (same length) considering how many integers are equal per position
        @param sig1: array of integers with signature
        @param sig2: other signature to compare
        @return: average of positions in arrays that are equal in both signatures
    '''
    return jaccard_similarity_score(sig1, sig2);



def minHashing(allSets):
    '''
        Builds a minhash signature for all the entry sets.
            @param allSets - a set of document's shingle sets
            @return: a matrix containing the minhash signature of each document (each column represents one document).
    '''

    #Union of all the hashes
    U = SortedSet()
    for i in range(0,len(allSets)):
        U |= allSets[i]

   #Generation of 100 hash functions
    totalFunctions = 100
    div = 10967819 #Prime number bigger than 1'000.000. Other options: 2724299, 3770953, 4311301.
    functions = []
    for i in range(0,totalFunctions):
        def func1(x):
            a = random.randint(1,totalFunctions)
            b = random.randint(1,totalFunctions)
            return (a*x +b)%div
        functions.append(func1)

   #Min hash algorithm
    'Initialization--------------------------------------------'
    M_i_c = [[float("inf")] * len(allSets) for i in range(totalFunctions)]
    i = 1

    #Iterates over the union of all shingles' hashes
    for u in U:
        h_r = []
        #We calculate the hash functions for the specific row
        for h in range(0,len(functions)):
            result = functions[h](i)
            h_r.append(result)
        c_cont = 0
        #We iterate over the columns
        for c in allSets:
            if(c.__contains__(u)): #If the column contains the value u
                for hh in range(0,len(functions)):
                    if(h_r[hh]<M_i_c[hh][c_cont]):
                        M_i_c[hh][c_cont] = h_r[hh]
            c_cont+=1
        i+=1

    print M_i_c
    return M_i_c

def LHS(signature_vectors, threshold):
    '''
    Locality sensitive hashing, efficiently computes all pairs of documents that are, with high probability,
    over (or very close) the similarity threshold determined. Candidates are selected
        @param signature_vectors: 2-dimensional array, each row contains one document's signature
        @param threshold: double from 0 to 1, determines the similarity of the pairs that should be candidates
                (there can be false positives, i.e. candidate pairs that their similarity is not over threshold).
        @return: a set with all pairs of documents that are candidate to be similar with threshold determined
    '''
    sign_length = len(signature_vectors[0])
    print "signature length: " + str(sign_length)
    print "threshold required: " + str(threshold)
    root_res = sp.root(lambda r: (r/sign_length)**(1/r)-threshold, 2)
    #beware that r might not divide exactly sign_length (last band might be smaller than r)
    r = int(root_res['x'][0])
    print "number of rows: " + str(r)
    candidate_pairs = set()
    start_idx = 0
    end_idx = r
    #for each band in the signature we are going to hash each document
    while start_idx<sign_length:
        #print "band start: " + str(start_idx) + " band end: " + str(end_idx)

        #a hash with 2**32 buckets hits memory error in my laptop (2**16 is low and will
        #probably give more false positives as there will be more collisions of hashes)
        hash_buckets = [[-1]]*(2**16)
        #print "hash buckets length " + str(len(hash_buckets))
        for doc in range(len(signature_vectors)):
            # note that with this: str(signature_vectors[doc][start_idx:end_idx]))
            # we get a string like: [11,23] (instead of 1123), as the hash is a random function,
            #and equality is maintained this approach works.
            to_bucket = int(md5.new(''.join(str(signature_vectors[doc][start_idx:end_idx]))).hexdigest()[0:4], 16)
            if(hash_buckets[to_bucket][0]==-1):
                hash_buckets[to_bucket]=[doc]
            else:
                #if there are other documents in this bucket this means that in this band (unless hash collision)
                #the two documents are equal, and thus they should be considered as potentially similar with threshold
                #determined
                for doc_in_bucket in hash_buckets[to_bucket]:
                    #one might think that pairs of doc swapped can appear in the pairs,
                    #meaning that we would have in the candidate_pairs (1,2) and (2,1)
                    #that's not possible cause we iterate from lower doc to bigger document
                    #thus cannot generate (2,1).
                    candidate_pairs.add((doc_in_bucket,doc))
                hash_buckets[to_bucket].append(doc)

        #this takes care that the last bucket does not go over the end of the signature length
        start_idx = start_idx+r
        end_idx = end_idx +r
        if(end_idx> sign_length):
            end_idx = sign_length


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
    #we transpose to have the signatures of each document in a single array
    signature_matrix = np.array(minHashing([set1,set2])).T
    print signature_matrix
    print "number of documents: " + str(len(signature_matrix))
    print "number of hashes in each signature: " + str(len(signature_matrix[0]))
    print "signature similarity: " + str(compareSignatures(signature_matrix[0], signature_matrix[1]))
    LHS(signature_matrix, 0.5)

    
main()



