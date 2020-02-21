"""
    This file regroup the implementation of the :class:`CNode` object and the
    necessary for defining automatically the inherited class from their
    :class:`HxCItem` equivalent.
"""
import idc
from astnode import AbstractCItem, HxCType
from hx_citem import HxCItem, HxCExpr, HxCStmt
from bip.base.biptype import BipType
import cnode_visitor

class CNode(AbstractCItem):
    """
        Abstract class which allow to represent C expression and C statement
        decompiled from HexRays. This is an equivalent class to
        :class:`HxCItem` but is designed for visiting an AST generated by
        HexRays. The main advantage to use this class and its subclasses and
        not the :class:`HxCItem` is the additional features which it provides,
        such as:

        * access to the parent node,
        * access to the parent :class:`HxCFunc`,
        * visitor for nodes bellow the current one,
        * direct access to :class:`HxLvar` for :class:`~bip.hexrays.CNodeExprVar`.

        The parrent class :class:`AbstractCItem` also provides common
        functionnality with the :class:`HxCItem` objects. All subclasses of
        this class have the same behavior as the one from :class:`HxCItem`
        with just some aditional feature.

        .. todo:: implement low and high address ? (map ea from cfunc could may be help ?)

        This is an abstract class and no object of this class should ever be
        created. The static method :meth:`GetCNode` allow to create object 
        of the correct subclass which inherit from :class:`CNode`.
    """

    ############################# ITEM CREATION #############################

    def __init__(self, citem, hxcfunc, parent):
        """
            Constructor for the abstract class :class:`HxCItem` . This should
            never be used directly.

            .. todo:: add check for correct types ?

            :param citem: a ``citem_t`` object, in practice this should always
                be a ``cexpr_t`` or a ``cinsn_t`` object.
            :param hxcfunc: A :class:`HxCFunc` object corresponding to the
                function which contains this node/item.
            :param parent: An object which inherit from :class:`CNode`
                corresponding to the parent expression or statement of this
                object. This may be ``None`` if this node is the root of
                the AST tree for its function.
        """
        super(CNode, self).__init__(citem) # provide self._citem
        #: The function associated with this node. This is a :class:`HxCFunc`
        #:  object. This is private and should not be modify. Modifying this
        #:  attribute will not make any modification to the data stored in
        #:  IDA.
        self._hxcfunc = hxcfunc
        #: The parent node of this node. This should be an object which
        #:  inherit from :class:`CNode`. This may be ``None`` if this node
        #:  is the root node of the AST tree for its function. This is private
        #:  and should not be modify. Modifying this
        #:  attribute will not make any modification to the data stored in
        #:  IDA.
        self._parent = parent

    ################################## BASE #################################
    
    @property
    def closest_ea(self):
        """
            Property which return the closest address for this :class:`CNode`.
            
            By default this should be equivalent to the :meth:`~CNode.ea`
            property except if it return ``idc.BADADDR``, in this case it will
            try and get the address of the parent. If the most parrent node
            of this node (which should be the root node of the function) still 
            has no address, ``None`` is return.

            :return: An integer corresponding to the closest address for this
                node. If no address where found this method will return None.
        """
        ea = self.ea
        obj = self._parent
        while ea == idc.BADADDR and obj is not None:
            ea = obj.ea
            obj = obj._parent
        if ea == idc.BADADDR:
            return None
        else:
            return ea

    ########################### ACCESS PROPERTIES ############################

    @property
    def has_parent(self):
        """
            Property which return true if the :class:`CNode` as a parent. Only
            CNode which are root of a function should not have a parent.
        """
        return self._parent is not None
    
    @property
    def parent(self):
        """
            Property which return the parent of this :class:`CNode`. If this
            node does not have a parent a :class:`RuntimeError` exception
            will be raised.

            :return: A :class:`CNode` object parent of this node.
        """
        if self._parent is None:
            raise RuntimeError("CNode {} as not parent".format(self))
        return self._parent
    
    @property
    def cfunc(self):
        """
            Property returning the :class:`HxCFunc` to which this node is
            associated.

            :return: A :class:`HxCFunc` object corresponding to the function
                associated with this node.
        """
        return self._hxcfunc

    ########################### VISITOR METHODS ##############################

    def visit_cnode(self, callback):
        """
            Method which allow to visit this :class:`CNode` elements and all
            those bellow it. This is implemented using a DFS algorithm. This
            does not use the hexrays visitor. For more information about the
            implementation see :func:`~cnode_visitor.visit_dfs_cnode` (this
            method is just a wrapper).

            :param callback: A callable which will be called on this and all
                :class:`CNode` bellow it. The call should take only one
                argument which correspond to the :class:`CNode` currently
                visited.
        """
        cnode_visitor.visit_dfs_cnode(self, callback)

    def visit_cnode_filterlist(self, callback, filter_list):
        """
            Method which allow to visit :class:`CNode` elements which are
            of a type present in a list. Start with the current :class:`CNode`
            and look in all its children. This is implemented using
            a DFS algorithm. This does not use the hexrays visitor. For more
            information about the implementation see
            :func:`~cnode_visitor.visit_dfs_cnode_filterlist` (this method is just
            a wrapper).

            :param callback: A callable which will be called on all
                :class:`CNode` in the function decompiled by hexrays. The call
                should take only one argument which correspond to the
                :class:`CNode` currently visited.
            :param filter_list: A list of class which inherit from :class:`CNode`.
                The callback will be called only for the node from a class in this
                list.
        """
        cnode_visitor.visit_dfs_cnode_filterlist(self, callback, filter_list)

    def get_cnode_filter(self, cb_filter):
        """
            Method which return a list of :class:`CNode` for which a filter
            return true. Internally this use the :meth:`~CNode.visit_cnode`
            method which visit all nodes bellow (and including) the current
            one, this is just a usefull wrapper.

            :param cb_filter: A callable which take a :class:`CNode` in
                parameter and return a boolean. This callback will be called
                on all children nodes and all nodes for which it returns
                true will be added in a list which will be returned by this
                function.
            :return: A list of :class:`CNode` which have match the filter.
                This list is order in which the node have been visited (see
                :meth:`~CNode.visit_cnode` for more information).
        """
        l = []
        def _app_filt(cn):
            if cb_filter(cn):
                l.append(cn)
        self.visit_cnode(_app_filt)
        return l

    def get_cnode_filter_type(self, type_filter):
        """
            Method which return a list of :class:`CNode` of a particular
            type(s). Internally this use the :meth:`~HxCFunc.visit_cnode_filterlist`
            method which visit all nodes bellow and including the current one,
            this is just a usefull wrapper.

            :param type_filter: The type(s) of :class:`CNode` to get. Only
                :class:`CNode` matching the isinstance of this type will
                be returned. This can be a type, a class or a tuple (or list)
                of class and type.
            :return: A list of :class:`CNode` which have match the type.
                This list is order in which the node have been visited (see
                :meth:`~HxCFunc.visit_cnode` for more information).
        """
        l = []
        def _app_filt(cn):
            l.append(cn)
        self.visit_cnode_filterlist(_app_filt, type_filter)
        return l

    ########################### HELPER FUNCTIONS ############################

    @property
    def ignore_cast(self):
        """
            Property which return this node if it is not a cast or its child
            if it is a cast. This is designed for allowing to quickly ignore
            cast when going through some nodes.

            :return: The first :class:`CNode` which is not a cast.
        """
        # default implem. return self, cast implem. return child.ignore_cast
        return self

    ########################### CNODE CREATION #############################

    def _createChild(self, citem):
        """
            Internal method which allow to create a :class:`CNode` object
            from a ``citem_t`` child of the current node. This must be used
            by :class:`CNodeStmt` and
            :class:`CNodeExpr` for creating their child expression and
            statement. This method is used for having compatibility with
            the :class:`HxCItem` class.

            Internally this function is a wrapper on :meth:`GetCNode` which
            is call with the same function than this object and with this
            object as parent.
    
            :param citem: A ``citem_t`` from ida.
            :return: The equivalent node object to the ``citem_t`` for bip.
                This will be an object which inherit from :class:`CNode` .
        """
        return CNode.GetCNode(citem, self._hxcfunc, self)

    @staticmethod
    def GetCNode(citem, hxcfunc, parent):
        """
            Static method which allow to create an object of the correct child
            class of :class:`CNode` which is equivalent to a ``citem_t`` from
            ida. In particular it will be used for converting ``cexpr_t`` and
            ``cinsn_t`` from ida to :class:`CNodeExpr` and :class:`CNodeStmt`
            in bip.  If no :class:`CNode` child object exist corresponding to
            the ``citem`` provided a ``ValueError`` exception will be raised.
            
            This is the equivalent of :meth:`HxCItem.GetHxCItem` but for the
            :class:`CNode` . 

            .. note:: :class:`CNodeExpr` and :class:`CNodeStmt` should not used
                this function for creating child item but
                :meth:`CNode._createChild`.
    
            .. todo:: maybe return None instead of raising an exception ?
    
            :param citem: A ``citem_t`` from ida.
            :param hxcfunc: A :class:`HxCFunc` object corresponding to the
                function which contains this node/item.
            :param parent: An object which inherit from :class:`CNode`
                corresponding to the parent expression or statement of this
                object. This may be ``None`` if this node is the root of
                the AST tree for its function.
            :return: The equivalent object to the ``citem_t`` for bip. This
                will be an object which inherit from :class:`HxCItem` .
        """
        done = set()
        todo = set(CNode.__subclasses__())
        while len(todo) != 0:
            cl = todo.pop()
            if cl in done:
                continue
            if cl.is_handling_type(citem.op):
                return cl(citem, hxcfunc, parent)
            else:
                done.add(cl)
                todo |= set(cl.__subclasses__())
        raise ValueError("GetCNode could not find an object matching the citem_t type provided ({})".format(citem.op))

class CNodeExpr(CNode):
    """
        Abstract class for representing a C Expression decompiled from
        HexRays. This is an abstract class which is used as a wrapper on top
        of the ``cexpr_t`` object. This is the equivalent of the
        :class:`HxCExpr` class but which inherit from the :class:`CNode` and
        is made for visiting an AST.

        No object of this class should be instanstiated, for getting an
        expression the function :func:`~CNode.GetCNode` should be
        used.

        .. todo:: something better could be done here for avoiding code
            duplication of the :class:`HxCExpr` class.
    """

    def __init__(self, cexpr, hxcfunc, parent):
        """
            Constructor for the :class:`CNodeExpr` object. Arguments are
            used by the :class:`CNode` constructor.

            :param cexpr: A ``cexpr_t`` object from ida.
            :param hxcfunc: A :class:`HxCFunc` object corresponding to the
                function which contains this node/item.
            :param parent: An object which inherit from :class:`CNode`
                corresponding to the parent expression or statement of this
                object. This may be ``None`` if this node is the root of
                the AST tree for its function.
        """
        super(CNodeExpr, self).__init__(cexpr, hxcfunc, parent)
        #: The ``cexpr_t`` object from ida.
        self._cexpr = cexpr

    def __str__(self):
        """
            Surcharge for printing a CExpr
        """
        return "{}(ea=0x{:X}, ops={})".format(self.__class__.__name__, self.ea, self.ops)

    @property
    def ops(self):
        """
            Function which return the C Expressions child of this expression.
            This is used only when the expression is recursive.

            :return: A ``list`` of object inheriting from :class:`CNodeExpr`
                and child of the current expression.
        """
        return []

    @property
    def type(self):
        """
            Property which return the type (:class:`BipType`) of this
            expression.

            .. todo:: implement setter

            :return: An object which inherit from :class:`BipType` which
                correspond to the type of this object. Change to this type
                object will not change the type of this expression.
        """
        return BipType.GetBipType(self._cexpr.type)

    ################################### HELPERS ##############################

    def find_final_left_node(self):
        """
            Return the node which is the left most "final" expression (inherit
            from :class:`CNodeExprFinal`) bellow this node. If this
            node is a final expression it is returned.
        """
        obj = self
        while not isinstance(obj, CNodeExprFinal):
            if len(obj.ops) == 0:
                raise Exception("Node {} is not final nor have child expr".format(obj))
            obj = obj.ops[0]
        return obj

    def find_left_node_notmatching(self, li):
        """
            Find the most left node not matching some classes. If the current
            node does not match any classes in the list provided it will be
            returned.

            This function allow to bypass nodes to ignored. A common
            utilisation will be to bypass some unary operand for getting a
            final value or to bypass cast, reference or ptr derefence only.
            For getting the final node and ingore all other nodes see
            :meth:`~CNode.find_final_left_node`. If a node found is a "final"
            node (inherit from :class:`CNodeExprFinal`) it will always be
            returned.

            For example for ignoring cast and ref use:
            ``cn.find_left_node_notmatching([CNodeExprCast, CNodeExprRef])`` .
            
            :param li: A ``list`` or ``tuple`` of classes which inherit from
                :class:`CNodeExpr` to ignore.
            :return: A CNode object which is not of one of the class in
                ``li``.
        """
        obj = self
        while isinstance(obj, tuple(li)) and not isinstance(obj, CNodeExprFinal):
            obj = obj.ops[0]
        return obj

class CNodeStmt(CNode):
    """
        Abstract class for representing a C Statement as returned by hexrays.
        This is an abstract class which is a wrapper on top of the
        ``cinsn_t`` ida object. This is the equivalent of the
        :class:`HxCStmt` class but which inherit from the :class:`CNode` and
        is made for visiting an AST.

        No object of this class should be instanstiated, for getting an
        expression the function :func:`~CNode.GetCNode` should be
        used.

        A statement can contain one or more child statement and one or more
        child expression (:class:`HxCExpr`) object.
        By convention properties which will return child statement of an
        object will start with the prefix ``st_`` .
    """

    def __init__(self, cinsn, hxcfunc, parent):
        """
            Constructor for a :class:`CNodeStmt` object. Arguments are
            used by the :class:`CNode` constructor.

            :param cinsn: A ``cinsn_t`` from ida.
            :param hxcfunc: A :class:`HxCFunc` object corresponding to the
                function which contains this node/item.
            :param parent: An object which inherit from :class:`CNode`
                corresponding to the parent expression or statement of this
                object. This may be ``None`` if this node is the root of
                the AST tree for its function.
        """
        super(CNodeStmt, self).__init__(cinsn, hxcfunc, parent)
        #: The ``cinsn_t`` object from ida.
        self._cinsn = cinsn

    def __str__(self):
        """
            Surcharge for printing a CStmt.
        """
        return "{}(ea=0x{:X}, st_childs={})".format(self.__class__.__name__, self.ea, self.st_childs)

    @property
    def st_childs(self):
        """
            Property which return a list of the statements which are childs of
            this statement. This is used only when the statement is recursive,
            if not this will return an empty list.

            :return: A list of child statement of this object.
            :rtype: Objects which inherit from :class:`CNodeStmt` .
        """
        return []

    @property
    def expr_childs(self):
        """
            Property which return a list of the expression (:class:`CNodeExpr`)
            which are childs of this statement. This will not return childs
            expression of the statement child of the current object.

            :return: A list of child expression of this object.
            :rtype: Objects which inherit from :class:`CNodeExpr` .
        """
        return []

#: Dictionnary which contain an equivalence between the class which inherit
#:  from :class:`HxCItem` and the one which inherit from :class:`CNode`. This
#:  is used for automatically constructing the classes which inherit from
#:  :class:`CNode` dynamically and should not be modified by hand.
#:  It is initialized with the 3 base classes which have a constructor.
_citem2cnode = {
        HxCItem: CNode,
        HxCExpr: CNodeExpr,
        HxCStmt: CNodeStmt,
    }

#: Dictionnary which allows to add method to a particular CNode
#:  implementation. This is used by :func:`addCNodeMethod` for adding a method
#:  in a CNode class which does not exist (is not possible to implement) in
#:  the HxCItem class equivalent. When the object is created by
#:  ``buildCNode`` the method will be added.
#:  
#:  This dictionnary as the name of the class for key, and a parameter a list
#:  of tuples. Each tuple consist of the name of the method as first element
#:  follow by the function object.
_cnodeMethods = {}

def addCNodeMethod(cnode_name, func_name=None):
    """
        Decorator for a function, allow to add a method to a
        CNode class. This is for supporting to add method specific to a CNode
        which are not implemented (probably because it is not possible to do
        so) in their equivalent HxCItem class. This is design to be used in
        conjonction with the :func:`buildCNode` decorator, methods which are
        added this way should be done before calling it. If the method already
        exist it will be overwrite by this implementation, this allow to
        redefine base methods from the HxCExpr.
        Internally this use the ``_cnodeMethods`` global dictionnary.
        
        It is possible to add properties using this method, if no
        ``func_name`` parameter is provided the name of the getter will be
        taken (and so the property must have a getter name). It is possible
        to use ``property`` as a decorator but this will work only for getter:
        
        .. code-block:: py

            @addCNodeMethod(myclassname)
            @property #order of those decorator is important
            def my_new_property(self):
                \"\"\"
                    Documentation will be correctly seen when generating
                    the doc.
                \"\"\"
                pass # THE CODE

        .. todo:: correctly handle all property decorators

        .. warning::
        
            All methods/properties decorated by this functions should be
            defined before the creation of the corresponding CNode! Currently
            the simplest way to do this is by adding it at the end of the
            ``cnode.py`` files.

        :param str cnode_name: The name of the CNode class to which add the
            property.
        :param str func_name: The name to use for adding to the CNode class,
            if None the name of the function will be used.
    """
    global _cnodeMethods
    # check if the cnode is already present in the dict:
    if cnode_name not in _cnodeMethods:
        _cnodeMethods[cnode_name] = []
    # the real internal function decorator.
    def _internal_addcnodemeth(func):
        # select function name
        # TODO prop.fget/fset/fdel are the real function of a property
        fn = func_name
        if fn is None:
            if isinstance(func, property):
                fn = func.fget.__name__
            else:
                fn = func.__name__
        # adding the method in the dict
        _cnodeMethods[cnode_name].append((fn, func, ))
        # we let the method be define without change
        return func
    return _internal_addcnodemeth


def buildCNode(cls):
    """
        Class decorator for automatically building a class equivalent to the
        one pass in argument but which inherit from :class:`CNode` instead
        of :class:`HxCItem` .

        Internally this will:

        * find the equivalent of the base classes by looking
          in ``_citem2cnode`` .
        * create a class identicall to the one in arguments but with name
          change for being prefix by ``CNode`` instead of ``HxC``. Attributes
          of the class are copied into the new class.
        * set the new class created as global to this module (the cnode one,
          not the one it was used in).
    """
    global _citem2cnode
    # check we did not already created it
    if cls in _citem2cnode:
        raise AssertionError("Equivalent class for {} has already been created".format(cls.__name__))

    # start by creating tuples of base classes
    lb = []
    for b in cls.__bases__:
        if b not in _citem2cnode:
            raise AssertionError("Base class for {} does not exist: impossible to generate dynamically".format(cls.__name__))
        lb.append(_citem2cnode[b])

    # creating the dictionnary of attributes
    attr = dict(cls.__dict__) # create a copy of the dict
    attr["__module__"] = __name__ # change module to cnode
    attr["__doc__"] = "Copy of :class:`{}` but which inherit from :class:`CNode`.\nAutomatically created by :func:`~bip.hexrays.cnode.buildCNode`".format(cls.__name__)# change doc

    # getting the name of the new class
    cn_cls_nm = cls.__name__.replace("HxC", "CNode")

    # adding methods from _cnodeMethods if any
    if cn_cls_nm in _cnodeMethods:
        for na, f in _cnodeMethods[cn_cls_nm]:
            attr[na] = f

    # creating the new class
    cn_cls = type(
            cn_cls_nm, # change name
            tuple(lb), # bases classes
            attr
        )

    # adding it to this module
    globals()[cn_cls.__name__] = cn_cls

    # adding it to _citem2cnode
    _citem2cnode[cls] = cn_cls

    # return the old class we don't want to change it
    return cls


@addCNodeMethod("CNodeExprVar")
@property
def lvar(self):
    """
        Property which allow direct access to the :class:`~bip.hexrays.HxLvar`
        object referenced by this node.

        This method exist only for the :class:`~bip.hexrays.CNode`
        implementation.

        :return: the :class:`~bip.hexrays.HxLvar` object referenced by this
            node.
    """
    return self._hxcfunc.lvar_at(self.index)

@addCNodeMethod("CNodeExprVar")
@property
def lvar_name(self):
    """
        Property which allow to get the name of the
        :class:`~bip.hexrays.HxLvar` referenced by this node.

        This method exist only for the :class:`~bip.hexrays.CNode`
        implementation.

        :return: The name of the lvar as a string.
    """
    return self._hxcfunc.lvar_at(self.index).name

@addCNodeMethod("CNodeExprCast")
@property
def ignore_cast(self):
    """
        Property which return the first child expression of this node cast
        which is not a cast. This is implemented for all
        :class:`~bip.hexrays.CNode` for allowing to quickly ignore cast (see
        :meth:`~bip.hexrays.CNode.ignore_cast`). Multiple chained cast are
        handle.

        :return: A :class:`CNodeExpr` which is not a cast.
    """
    return self.operand.ignore_cast



