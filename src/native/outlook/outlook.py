### BITPIM
###
### Copyright (C) 2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"Be at one with Outlook"

# See this recipe on ASPN for how this code started
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/173216
# Chris Somerlot also gave some insights

import win32com.client

from pywintypes import com_error

# This is the complete list of field names available
##    Account
##    AssistantName
##    AssistantTelephoneNumber
##    BillingInformation
##    Body
##    Business2TelephoneNumber
##    BusinessAddress
##    BusinessAddressCity
##    BusinessAddressCountry
##    BusinessAddressPostOfficeBox
##    BusinessAddressPostalCode
##    BusinessAddressState
##    BusinessAddressStreet
##    BusinessFaxNumber
##    BusinessHomePage
##    BusinessTelephoneNumber
##    CallbackTelephoneNumber
##    CarTelephoneNumber
##    Categories
##    Children
##    Class
##    Companies
##    CompanyAndFullName
##    CompanyLastFirstNoSpace
##    CompanyLastFirstSpaceOnly
##    CompanyMainTelephoneNumber
##    CompanyName
##    ComputerNetworkName
##    ConversationIndex
##    ConversationTopic
##    CustomerID
##    Department
##    Email1Address
##    Email1AddressType
##    Email1DisplayName
##    Email1EntryID
##    Email2Address
##    Email2AddressType
##    Email2DisplayName
##    Email2EntryID
##    Email3Address
##    Email3AddressType
##    Email3DisplayName
##    Email3EntryID
##    EntryID
##    FTPSite
##    FileAs
##    FirstName
##    FullName
##    FullNameAndCompany
##    Gender
##    GovernmentIDNumber
##    Hobby
##    Home2TelephoneNumber
##    HomeAddress
##    HomeAddressCity
##    HomeAddressCountry
##    HomeAddressPostOfficeBox
##    HomeAddressPostalCode
##    HomeAddressState
##    HomeAddressStreet
##    HomeFaxNumber
##    HomeTelephoneNumber
##    ISDNNumber
##    Importance
##    Initials
##    InternetFreeBusyAddress
##    JobTitle
##    Journal
##    Language
##    LastFirstAndSuffix
##    LastFirstNoSpace
##    LastFirstNoSpaceCompany
##    LastFirstSpaceOnly
##    LastFirstSpaceOnlyCompany
##    LastName
##    LastNameAndFirstName
##    MailingAddress
##    MailingAddressCity
##    MailingAddressCountry
##    MailingAddressPostOfficeBox
##    MailingAddressPostalCode
##    MailingAddressState
##    MailingAddressStreet
##    ManagerName
##    MessageClass
##    MiddleName
##    Mileage
##    MobileTelephoneNumber
##    NetMeetingAlias
##    NetMeetingServer
##    NickName
##    NoAging
##    OfficeLocation
##    OrganizationalIDNumber
##    OtherAddress
##    OtherAddressCity
##    OtherAddressCountry
##    OtherAddressPostOfficeBox
##    OtherAddressPostalCode
##    OtherAddressState
##    OtherAddressStreet
##    OtherFaxNumber
##    OtherTelephoneNumber
##    OutlookInternalVersion
##    OutlookVersion
##    PagerNumber
##    PersonalHomePage
##    PrimaryTelephoneNumber
##    Profession
##    RadioTelephoneNumber
##    ReferredBy
##    Saved
##    SelectedMailingAddress
##    Sensitivity
##    Size
##    Spouse
##    Subject
##    Suffix
##    TTYTDDTelephoneNumber
##    TelexNumber
##    Title
##    UnRead
##    User1
##    User2
##    User3
##    User4
##    UserCertificate
##    WebPage
##    YomiCompanyName
##    YomiFirstName
##YomiLastName

TRACE=1

def _getkeys(folder):
    ofContacts=folder

    contact = ofContacts.Items.Item(1) # look at keys on first contact
    keys = []
    for key in contact._prop_map_get_:
        if True or isinstance(getattr(contact, key), (int, str, unicode)):
            keys.append(key)
    if TRACE:
        keys.sort()
        print "Fields\n======================================"
        for key in keys:
            print key
    return keys


def _getcontacts(folder, keys):

    records=[]
    
    # this should use more try/except blocks or nested blocks
    ofContacts =  folder

    if TRACE:
        print "number of contacts:", ofContacts.Items.Count

    for oc in range(ofContacts.Items.Count):
        record=[]
        # COM never could make up its mind whether indexes start at zero or
        # one.  Raymond Chen's weblog details why.
        contact = ofContacts.Items.Item(oc + 1)
        if contact.Class == win32com.client.constants.olContact:
            record = []
            for key in keys:
                record.append(getattr(contact, key))
            if TRACE:
                print oc, getattr(contact, 'FullName')
            records.append(record)
    return records

def getcontacts(folder):
    """Returns a list of lists (same as output of DSV) with the first row
    being a header and the rest being each entry from Outlook contacts"""
    
    keys=["EntryID", "Account", "WebPage", "OutlookInternalVersion", "OutlookVersion"]

    return _getcontacts(folder, keys)

def getfolderfromid(id, default=False):
    """Returns a folder object from the supplied id

    @param id: The id of the folder
    @param default: If true and the folder can't be found, then return the default"""
    onMAPI = getmapinamespace()
    try:
        folder=onMAPI.GetFolderFromID(id)
    except com_error,e:
        folder=None
        
    # ::TODO:: should be supplied default type (contacts, calendar etc)
    if not folder:
        folder=onMAPI.GetDefaultFolder(win32com.client.constants.olFolderContacts)
    return folder

def getfoldername(folder):
    n=[]
    while folder:
        try:
            n=[folder.Name]+n
        except AttributeError:
            break # namespace object has no 'Name'
        folder=folder.Parent
    return " / ".join(n)

def getfolderid(folder):
    return folder.EntryID

def pickfolder():
    return getmapinamespace().PickFolder()

_outlookappobject=None
def getoutlookapp():
    global _outlookappobject
    if _outlookappobject is None:
        if __debug__:
            # ensure stubs are generated in developer code
            win32com.client.gencache.EnsureDispatch("Outlook.Application.9")
        _outlookappobject=win32com.client.Dispatch("Outlook.Application.9")
    return _outlookappobject

_mapinamespaceobject=None
def getmapinamespace():
    global _mapinamespaceobject
    if _mapinamespaceobject is None:
        _mapinamespaceobject=getoutlookapp().GetNamespace("MAPI")
    return _mapinamespaceobject


if __name__=='__main__':
    oOutlookApp=win32com.client.Dispatch("Outlook.Application.9")
    onMAPI = oOutlookApp.GetNamespace("MAPI")

    res=onMAPI.PickFolder()
    print res
    # print _getkeys(res)
    print getcontacts(res)
