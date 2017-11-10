from nltk import ngrams
import md5
from sortedcontainers import SortedSet
import random
from sklearn.metrics import jaccard_similarity_score
import scipy.optimize as sp
import numpy as np
import sys
        
def shingle_text(text, k):
    '''
    Takes a text and partitions it in hashed (4 byte hash) shingles of length k.
        @param text: string containing the text to shingle
        @param k: number of characters in a shingle
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
    Returns Jaccard similarity index between the two sets.
        @param set1: first set
        @param set2: second set
        @return: ratio of items in the intersection of the sets vs all distinct items in both sets
    '''
    return float(len(set1 & set2)) / len(set1 | set2)

def compareSignatures(sig1,sig2):
    '''
    Compares two arrays of integers (same length) considering how many integers are equal per position.
        @param sig1: array of integers with signature
        @param sig2: other signature to compare
        @return: average of positions in arrays that are equal in both signatures
    '''
    #jaccard similarity in sklearn.metrics uses the definition of position comparison between signatures
    #see http://scikit-learn.org/stable/modules/model_evaluation.html#jaccard-similarity-score
    #Thus it is a different metric than the one used in compareSets(.,.)
    return jaccard_similarity_score(sig1, sig2);

def minHashing(allSets):
    '''
    Builds a minhash signature for all the entry sets, with each signature containing 100 integers.   
        @param allSets - a set of document's shingle sets
        @return: a matrix containing the minhash signature of each document (each column represents one document).
    '''

    print "Computing MinHash"
    #Union of all the shingle hashes that we have in the sets
    #Note that we only have to operate over them as the other rows/hashes will be 0 for all documents
    U = SortedSet()
    for i in range(0,len(allSets)):
        U |= allSets[i]

    #Generation of 100 hash functions
    totalFunctions = 100
    #to avoid collisions we make the number of buckets in the hash (determined by mod) very big.
    #Ideally, we would make this number larger than 2^32 (number of shingle hashes), but in order to
    #have a reasonable bucket list in LSH function without collision we reduced this modulus number.
    mod = 2971215073
    #we also choose high parameters for a and b for the modulus in order to avoid having a hash function
    #that does not permute the rows (equivalent to identity function) 
    low = 1000
    high = 1000000
    functions = []
    for i in range(0,totalFunctions):
        def func1(x):
            a = random.randint(low,high)
            b = random.randint(low,high)
            return (a*x +b)%mod
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
    
    print "Finished computing MinHash"
    return M_i_c

def LSH(signature_vectors, threshold):
    '''
    Locality sensitive hashing, efficiently computes all pairs of documents that are, with high probability,
    over (or very close) the similarity threshold determined. Candidates are selected
        @param signature_vectors: 2-dimensional array, each row contains one document's signature
        @param threshold: double from 0 to 1, determines the similarity of the pairs that should be candidates
                (there can be false positives, i.e. candidate pairs that their similarity is not over threshold).
        @return: a set with all pairs of documents that are candidate to be similar with threshold determined
    '''
    print "Computing LSH"
    sign_length = len(signature_vectors[0])
    print "threshold required: " + str(threshold)
    root_res = sp.root(lambda r: (r/sign_length)**(1/r)-threshold, 2)
    #beware that r might not divide exactly sign_length (last band might be smaller than r)
    r = int(root_res['x'][0])
    print "number of rows in a band of LSH: " + str(r)
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
            # and equality is maintained this approach works.
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

    print "Finished computing LSH"
    return candidate_pairs

def main(t=0.8):
    #we set the shingle length to most used value for documents
    k=10
    
    with open("dataset.txt") as dataset:
        allSets = []
        for line in dataset:
            allSets.append(shingle_text(line, k))
        
        print "number of documents: " + str(len(allSets))
        print "Lenght of shingled set for first document:"
        print len(allSets[0])
        print "Jaccard Similarity between sets 0 and 1 (representing documents 0 and 1)"
        print compareSets(allSets[0], allSets[1])
        print "Jaccard Similarity between sets 0 and 6 (they are the same text with some sentences missing on 6)"
        print compareSets(allSets[0], allSets[6])
        print "Jaccard Similarity between sets 0 and 14 (14 is half the text of 0)"
        print compareSets(allSets[0], allSets[14])
        
        #we apply minHashing to all sets to obtain each document's signature. 
        #we transpose the matrix to have the signatures of each document in a single array.
        signature_matrix = np.array(minHashing(allSets)).T
        
        print "number of hashes in each signature: " + str(len(signature_matrix[0]))
        print "Similarity between signatures of 0 and 1"
        print compareSignatures(signature_matrix[0], signature_matrix[1])
        print "Similarity between signatures 0 and 6"
        print compareSignatures(signature_matrix[0], signature_matrix[6])
        print "Similarity between signatures 0 and 14"
        print compareSignatures(signature_matrix[0], signature_matrix[14])
        
        candidate_pairs = LSH(signature_matrix, t)
        print "Pairs that are candidates to be similar with threshold " + str(t)
        print candidate_pairs
        similar_pairs = []
        for pair in candidate_pairs:
            #instead of comparing signatures here we could compare shingle sets or even the documents themselves.
            #we would spend more resources but avoid more false positives
            if(compareSignatures(signature_matrix[pair[0]], signature_matrix[pair[1]])):
                similar_pairs.append(pair)
                
        print "Pairs that are similar with threshold " + str(t) + " (although there can be some false negatives and positives)"
        print similar_pairs

try:
    main(float(sys.argv[1]))
except:
    main()



