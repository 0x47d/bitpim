### BITPIM
###
### Copyright (C) 2003 Alan Pinstein <apinstein@mac.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

import re

# class to read a single vCard entry from a stream
class vCard:
    # LG-phone supported attributes
    fullname = ""
    email1 = ""
    email2 = ""
    email3 = ""
    home_ph = ""
    home2_ph = ""
    work_ph = ""
    work2_ph = ""
    cell_ph = ""
    cell2_ph = ""
    pager_ph = ""
    fax_ph = ""
    fax2_ph = ""

    # reset
    def reset(self):
        self.fullname = ""
        self.email1 = ""
        self.email2 = ""
        self.email3 = ""
        self.home_ph = ""
        self.home2_ph = ""
        self.work_ph = ""
        self.work2_ph = ""
        self.cell_ph = ""
        self.cell2_ph = ""
        self.pager_ph = ""
        self.fax_ph = ""
        self.fax2_ph = ""
        
    # string rep of object
    def __str__(self):
        return "Name: " + self.fullname + "\n" \
               + "Home: " + self.home_ph + "\n" \
               + "Home2: " + self.home2_ph + "\n" \
               + "Work: " + self.work_ph + "\n" \
               + "Work2: " + self.work2_ph + "\n" \
               + "Cell: " + self.cell_ph + "\n" \
               + "Cell2: " + self.cell2_ph + "\n" \
               + "Pager: " + self.pager_ph + "\n" \
               + "Fax: " + self.fax_ph + "\n" \
               + "Fax2: " + self.fax2_ph + "\n" \
               + "Email1: " + self.email1 + "\n" \
               + "Email2: " + self.email2 + "\n" \
               + "Email3: " + self.email3
    
    # functions below 
    # call this routine with a stream handle
    # function expects that the first line will contain BEGIN:VCARD
    # function will read a single vCard entry out of the stream and into this class
    # function returns -1 if the stream doesn't have a BEGIN:VCARD on first line
    # function returns 0 if everything was successful
    def readvCard(self, h):
        # make sure we're at the beginning of a vCard entry
        line = h.readline()
        if line.lower().find("begin:vcard") == -1:
            return -1
        
        # now read each line until a end:vcard is found, populating the class as understandable values are encountered
        while line.lower().find("end:vcard") == -1:
            self.parsevCardLine(line)
            line = h.readline() [:-1]
        return 0

    # check the passed vCard line for useful info
    # respect maximum lengths by silently truncating
    def parsevCardLine(self, line):
        # separate fieldname & data
        info = line.split(":", 1)
        # separate fieldname modifiers
        infoBits = info[0].split(";")
        if infoBits[0].lower() == "email":
            if self.email1 == "":
                self.email1 = info[1] [:48]
            elif self.email2 == "":
                self.email2 = info[1] [:48]
            elif self.email3 == "":
                self.email3 = info[1] [:48]
            else:
                print "Already found 3 emails. No more will fit."
        elif infoBits[0].lower() == "fn":
            names = info[1].split(" ", 1)
            if len(names) == 2:
                self.fullname = names[1] + " " + names[0]
            else:
                self.fullname = info[1]
            self.fullname = self.fullname [:22]
        elif infoBits[0].lower() == "tel":
            # grab phone numbers, but grab DIGITS only
            t = re.compile('\D')
            for bit in infoBits:
                if bit.lower().find("type=") != -1:
                    type = bit [5:]
                    if type.lower() == "home":
                        if self.home_ph == "":
                            self.home_ph = t.sub('', info[1]) [:48]
                        elif self.home2_ph =="":
                            self.home2_ph = t.sub('', info[1]) [:48]
                        else:
                            print "Already found 2 home numbers. No more will fit."
                    if type.lower() == "work":
                        if self.work_ph == "":
                            self.work_ph = t.sub('', info[1]) [:48]
                        elif self.work2_ph =="":
                            self.work2_ph = t.sub('', info[1]) [:48]
                        else:
                            print "Already found 2 work numbers. No more will fit."
                    if type.lower() == "cell":
                        if self.cell_ph == "":
                            self.cell_ph = t.sub('', info[1]) [:48]
                        elif self.cell2_ph =="":
                            self.cell2_ph = t.sub('', info[1]) [:48]
                        else:
                            print "Already found 2 cell numbers. No more will fit."
                    if type.lower() == "fax":
                        if self.fax_ph == "":
                            self.fax_ph = t.sub('', info[1]) [:48]
                        elif self.fax2_ph =="":
                            self.fax2_ph = t.sub('', info[1]) [:48]
                        else:
                            print "Already found 2 fax numbers. No more will fit."
                    elif type.lower() == "pager":
                        self.pager_ph = t.sub('', info[1]) [:48]
                    
        
# program main
class vCardImporter:
    phonebook = {}

    # import the passed vCard file
    def importFile(self, path):
        counter=0
        blankentry={ 'name': "", 'group': 0, 'type1': 0, 'type2': 0, 'type3': 0, 'type4': 0, 'type5': 0, 'number1': "", 'number2': "", 'number3': "", 'number4': "", 'number5': "", 'email1': "", 'email2': "", 'email3': "", 'memo': "", 'msgringtone': 0, 'ringtone': 0, 'secret': False, 'serial1': 0, 'serial2': 0, 'url': "", '?offset00f': 0, '?offset028': 0, '?offset111': 0, '?offset20c': 0 }
        typemap = { 'home' : 0,
                    'home2' : 1,
                    'office' : 2,
                    'office2' : 3,
                    'mobile' : 4,
                    'mobile2' : 5,
                    'pager' : 6,
                    'fax' : 7,
                    'fax2' : 8,
                    'none' : 9 }

        f = open(path)
        contact = vCard()
        # iterate through file until no more entries found
        while contact.readvCard(f) != -1:
            # create phbook entry
            entry = blankentry.copy()
            entry['name'] = contact.fullname
            # each contact can have up to 5 numbers, each with its own label
            num = 1
            if contact.home_ph != "" and num <= 5:
                entry['number' + str(num)] = contact.home_ph
                entry['type' + str(num)] = typemap['home']
                num += 1
            if contact.work_ph != "" and num <= 5:
                entry['number' + str(num)] = contact.work_ph
                entry['type' + str(num)] = typemap['office']
                num += 1
            if contact.cell_ph != "" and num <= 5:
                entry['number' + str(num)] = contact.cell_ph
                entry['type' + str(num)] = typemap['mobile']
                num += 1
            if contact.pager_ph != "" and num <= 5:
                entry['number' + str(num)] = contact.pager_ph
                entry['type' + str(num)] = typemap['pager']
                num += 1
            if contact.home2_ph != "" and num <= 5:
                entry['number' + str(num)] = contact.home2_ph
                entry['type' + str(num)] = typemap['home2']
                num += 1
            if contact.work2_ph != "" and num <= 5:
                entry['number' + str(num)] = contact.work2_ph
                entry['type' + str(num)] = typemap['office2']
                num += 1
            if contact.cell2_ph != "" and num <= 5:
                entry['number' + str(num)] = contact.cell2_ph
                entry['type' + str(num)] = typemap['mobile2']
                num += 1
            if contact.fax_ph != "" and num <= 5:
                entry['number' + str(num)] = contact.fax_ph
                entry['type' + str(num)] = typemap['fax']
                num += 1
            if contact.fax2_ph != "" and num <= 5:
                entry['number' + str(num)] = contact.fax2_ph
                entry['type' + str(num)] = typemap['fax2']
                num += 1

            # and up to 3 emails, with no labels
            entry['email1'] = contact.email1
            entry['email2'] = contact.email2
            entry['email3'] = contact.email3
            self.phonebook[counter] = entry
            counter += 1
            contact.reset()

        print "Found and processed " + str(counter) + " vCard entries."
        f.close()

    def getIndexFile(self):
        return "result['phonebook']="+`self.phonebook`

    def writeIndexFile(self):
        # write out entries to an index file
        f=open("index.idx", "w")
        f.write(self.getIndexFile())
        f.close()

if __name__ == "__main__":
    print "Main test"
    i = vCardImporter()
    i.importFile("/Users/aspinste/Desktop/to-cellphone.vcf")
    print i.getIndexFile()
