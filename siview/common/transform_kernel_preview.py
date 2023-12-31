# Python modules


# 3rd party modules


# Our modules


class TransformKernelPreview(object):
    """A lightweight version of a transform kernel that's good for populating
       lists of kernels (as in the transform kernel manage dialog).
    """    
    def __init__(self, attributes=None):
        self.id = ""
        self.uuid = ""
        self.name = ""
        self.menu_label = ""
        self.creator = ""
        self.created = ""
        self.is_public = False
        self.comment = ""
        # referrers is a (possibly empty) list of 2-tuples of (id, name).
        # This contains all of the pulse sequences that refer to this 
        # pulse project.
        self.referrers = [ ]

        if attributes is not None:
            self.inflate(attributes)
            
        if self.comment is None:
            self.comment = ""


    def __str__(self):
        return self.__unicode__()


    def __unicode__(self):
        lines = [ ]
        lines.append("--- Preview of Transform Kernel %s ---" % self.id) 
        lines.append("Name: %s" % self.name)
        lines.append("Menu Label: %s" % self.menu_label)  
        lines.append("Public: %s" % ("True" if self.is_public else "False"))
        lines.append("comment: %s" % self.comment[:100]) 

        # __unicode__() must return a Unicode object. In practice the code
        # above always generates Unicode, but we ensure it here.
        return '\n'.join(lines)
        
        
    @property
    def is_frozen(self):
        """A pulse project is frozen when it's public or when one or more
        pulse sequences refers to it."""
        return bool(self.referrers) or self.is_public


    def inflate(self, source):
        if hasattr(source, "makeelement"):
            # Quacks like an ElementTree.Element
            
            # PulseProjectPreview are never deflated to XML, so there's no
            # support for inflating them from XML
            raise NotImplementedError
            
        elif hasattr(source, "keys"):
            # Quacks like a dict
            for key in list(source.keys()):
                if hasattr(self, key):
                    setattr(self, key, source[key])



