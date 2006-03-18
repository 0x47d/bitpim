<html>
<head><title>_HELP_TITLE</title>
#ifdef APPLETITLE
<META NAME="AppleTitle" CONTENT=APPLETITLE>
#endif
<LINK rel="stylesheet"
      href="../bitpim.css"
      type="text/css">
</head>

<body>

#define URL(link,desc) <a href=\"link\" target="bitpimhelpexternallink">desc</a>

#define CONCAT #1#2

#define BEGIN_TOC <p>

#define END_TOC <br>

#define TOC_0 <ul>
#define ENDTOC_0 </ul>
#define TOCITEM_0(text,link) <li><a href=\"link\">text</a>

#define TOC_1 TOC_0
#define TOC_2 TOC_1
#define TOCITEM_1 TOCITEM_0

#define ENDTOC_1 ENDTOC_0
#define ENDTOC_2 ENDTOC_1




#define BUTTON(file, title, icon) \
   <a HREF=\"file\"> \
   <img align=center height="30" width="30" src=\"CONCAT(icon,.png)\" BORDER=0 ALT=\"title\"></A>

#define BLANKBUTTON(file) \
   <img align=center height="30" width="30" src=\"CONCAT(file,.png)\" BORDER=0 ALT="">

#define SCREENSHOT(file, description) \
   <img align=center src=\"CONCAT(file,.png)\" BORDER=0 ALT=\"description\">

#define TEXTLINK(file,title,desc) \
   <b>desc:</b> <a href=\"file\">title</a>&nbsp;&nbsp;

<h1>_HELP_TITLE</h1>

