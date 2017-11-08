from ordered_set import OrderedSet
from nltk import ngrams
import md5

'''
Hashes in text:
    Since documents are much shorter than 2³² (32 bits hash combinations),
    we still can be sure that a document is only a small fraction of
    the possible tokens in it's sets.
'''
'''
Collision of hashes:
    There's a small chance of a collision where two shingles hashed to
    the same token, but that could make two documents appear to have shingles in common.
    
    But the number of different strings of length k=10 that will actually appear in
    any document is much smaller than 26¹⁰ (26 alphabet characters) and also smaller 
    than 256¹⁰ (256 ASCII characters).

'''        
        
def shingle_text(text, k):
    '''
    single_text: takes a text and partitions it in hashed (4 byte hash) shingles of length k.
        @param text: string containing the text to shingle
        @param k: length of the characters in a shingle
        @return: ordered (by input order) set containing all hashes.
    '''
    shingled_text = OrderedSet()
    #shingled by character (counting space as character too)
    kgram = ngrams(text,k)
    for gram in kgram:
        #hash the shingle into a token
        shingled_text.add(md5.new(''.join(gram)).hexdigest()[0:8])
    return shingled_text



def main():
    text="try text"
    k=3
    shingle_text(text, k)
    
    
main()