#!/usr/bin/env python

# Do string matching giving a confidence score.

import difflib

# according to doc, should call set_seq2 once and then keep changing
# seq1

def match(s1, s2):
    s=difflib.SequenceMatcher()
    s.set_seq2(s1)
    s.set_seq1(s2)
    return int(s.ratio()*100)

inp="""
John Smith
JohnSmith
John Q Smith
Smith John
JQ Smith
Smith J
Matrix Revolutions
Matty Ranger
Smith John Q
John Smi
Smithy
John
Joe Blow
Jo Bloggs
Joe Bloggs
Mary Miggins
John Q Bloggs
Verizon
VZW
American Airlines"""

inp=[x for x in inp.split("\n") if len(x)]
for one in inp:
    print "=================="
    print one
    print
    l=[]
    for two in inp:
        l.append( (match(one, two), two) )
    l.sort()
    l.reverse()
    for score,name in l:
        print "%3d %s" % (score,name)
    print
