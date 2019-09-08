# -*- coding: utf-8 -*-

import json
import inspect

from typing import Any
from typing import Set
from typing import Dict
from typing import List
from typing import Union
from typing import Optional
from typing import Sequence

from .types import Type as T
from .types import Types as U

from .utils import StrictFields
from .flags import ChannelOptions
from .flags import FunctionOptions

from .tokenizer import Token
from .tokenizer import TokenType
from .tokenizer import TokenValue

class Node(metaclass = StrictFields):
    vt   : Optional[T]
    row  : int
    col  : int
    file : str

    # don't initialize these fields in the generated constructor
    __noinit__ = {
        'vt',
        'row',
        'col',
        'file',
    }

    def __init__(self, tk: Token):
        self.row = tk.row
        self.col = tk.col
        self.file = tk.file

        # noinspection PyUnresolvedReferences
        # special case for the `vt` attribute, the `__attr__` is a set of
        # all class attr names, it is added by the `StrictFields` metaclass
        if 'vt' not in self.__attrs__:
            self.vt = None

    def __repr__(self) -> str:
        return json.dumps(self._build(set()), indent = 4)

    def _build(self, path: Set[int]) -> Dict[str, Any]:
        if id(self) in path:
            return {}

        # add to path
        ret = {'__class__': self.__class__.__name__}
        path.add(id(self))

        # dump every exported attrs, except "row", "col" and "file"
        for attr in dir(self):
            if attr == 'row' or \
               attr == 'col' or \
               attr == 'file' or \
               attr.endswith('_') or \
               attr.startswith('_') or \
               inspect.ismethod(getattr(self, attr)):
                continue
            elif attr != 'vt':
                ret[attr] = self._build_val(path, getattr(self, attr))
            elif self.vt is not None:
                ret[attr] = str(self.vt)
            else:
                ret[attr] = None

        # all done
        path.remove(id(self))
        return ret

    def _build_val(self, path: Set[int], val: Any) -> Any:
        if isinstance(val, Node):
            return val._build(path)
        elif isinstance(val, bytes):
            return val.decode('unicode_escape')
        elif isinstance(val, dict):
            return self._build_dict(path, val)
        elif isinstance(val, (list, tuple)):
            return self._build_list(path, val)
        else:
            return val

    def _build_list(self, path: Set[int], val: Sequence[Any]) -> List[Any]:
        return [self._build_val(path, item) for item in val]

    def _build_dict(self, path: Set[int], val: Dict[Any, Any]) -> Dict[Any, Any]:
        return {key: self._build_val(path, value) for key, value in val.items()}

### Basic Elements ###

class Value(Node):
    kind  : TokenType
    value : TokenValue

    def __init__(self, tk: Token):
        super().__init__(tk)
        self.value = tk.value
        assert tk.kind == self.kind

class Int(Value):
    vt   = U.UntypedInt
    kind = TokenType.Int

class Name(Value):
    kind = TokenType.Name

class Rune(Value):
    vt   = U.UntypedRune
    kind = TokenType.Rune

class Float(Value):
    vt   = U.UntypedFloat
    kind = TokenType.Float

class String(Value):
    vt   = U.UntypedString
    kind = TokenType.String

class Complex(Value):
    vt   = U.UntypedComplex
    kind = TokenType.Complex

class Operator(Value):
    kind = TokenType.Operator

### Language Structures ###

class MapType(Node):
    key  : 'Type'
    elem : 'Type'

class ArrayType(Node):
    len  : 'Expression'
    elem : 'Type'

class SliceType(Node):
    elem: 'Type'

class NamedType(Node):
    name    : Name
    package : Optional[Name]

class StructType(Node):
    fields: List['StructField']

class StructField(Node):
    type: 'Type'
    name: Optional[Name]
    tags: Optional[String]

class ChannelType(Node):
    dir  : ChannelOptions
    elem : 'Type'

class PointerType(Node):
    base: 'Type'

class FunctionType(Node):
    type: 'FunctionSignature'

class FunctionArgument(Node):
    name: Optional[Name]
    type: 'Type'

class FunctionSignature(Node):
    var  : bool
    args : List[FunctionArgument]
    rets : List[FunctionArgument]

class InterfaceType(Node):
    decls: List[Union[
        NamedType,
        'InterfaceMethod',
    ]]

class InterfaceMethod(Node):
    name: Name
    type: FunctionSignature

Type = Union[
    MapType,
    ArrayType,
    SliceType,
    NamedType,
    StructType,
    ChannelType,
    PointerType,
    FunctionType,
    InterfaceType,
]

class Primary(Node):
    val  : 'Operand'
    mods : List['Modifier']

class Conversion(Node):
    type  : Type
    value : 'Expression'

class Expression(Node):
    op    : Optional[Operator]
    left  : Union[Primary, 'Expression']
    right : Optional['Expression']

    def is_call(self) -> bool:
        if self.op is not None:
            return False
        elif self.right is not None:
            return False
        elif not isinstance(self.left, Primary):
            return False
        elif not self.left.mods:
            return False
        else:
            return isinstance(self.left.mods[-1], Arguments)

class Lambda(Node):
    body      : 'CompoundStatement'
    signature : FunctionSignature

class VarArrayType(Node):
    elem: Type

LiteralType = Union[
    MapType,
    ArrayType,
    NamedType,
    SliceType,
    StructType,
    VarArrayType,
]

class LiteralValue(Node):
    items: List['Element']

class Element(Node):
    key   : Optional[Union[Expression, LiteralValue]]
    value : Union[Expression, LiteralValue]

class Composite(Node):
    type  : Optional[LiteralType]
    value : LiteralValue

Constant = Union[
    Int,
    Rune,
    Float,
    String,
    Complex,
]

Operand = Union[
    Name,
    Lambda,
    Constant,
    Composite,
    Conversion,
    Expression,
]

class Index(Node):
    expr: Expression

class Slice(Node):
    pos: Optional[Expression]
    len: Optional[Expression]
    cap: Optional[Union[bool, Expression]]

class Selector(Node):
    attr: Name

class Arguments(Node):
    var  : bool
    args : List[Union[Type, Expression]]

class Assertion(Node):
    type: Optional[Type]

Modifier = Union[
    Index,
    Slice,
    Selector,
    Arguments,
    Assertion,
]

### Top Level Declarations ###

class LinkSpec(Node):
    name: str
    link: str

class InitSpec(Node):
    type   : Optional[Type]
    names  : List[Name]
    values : List[Expression]
    consts : bool

class TypeSpec(Node):
    name  : Name
    type  : 'Type'
    alias : bool

class Function(Node):
    name: Name
    opts: FunctionOptions
    type: FunctionSignature
    recv: Optional[FunctionArgument]
    body: Optional['CompoundStatement']

class ImportC(Node):
    src: str

    def __init__(self, tk: Token):
        self.src = tk.value
        super().__init__(tk)
        assert tk.kind == TokenType.Comments

class ImportHere(Node):
    def __init__(self, tk: Token):
        super().__init__(tk)
        assert tk.kind == TokenType.Operator and tk.value == '.'

class ImportSpec(Node):
    path  : String
    alias : Optional[Union[Name, ImportC, ImportHere]]

class Package(Node):
    name    : Name
    vars    : List[InitSpec]
    links   : List[LinkSpec]
    funcs   : List[Function]
    types   : List[TypeSpec]
    consts  : List[InitSpec]
    imports : List[ImportSpec]

### Statements -- Basic Structures ###

class Go(Node):
    expr: Expression

class If(Node):
    cond   : Expression
    init   : 'SimpleStatement'
    body   : 'CompoundStatement'
    branch : Optional[Union['If', 'CompoundStatement']]

class For(Node):
    cond: Optional[Expression]
    init: Optional['SimpleStatement']
    post: Optional['SimpleStatement']
    body: 'CompoundStatement'

class ForRange(Node):
    svd   : bool
    expr  : Expression
    body  : 'CompoundStatement'
    terms : List[Union[Name, Expression]]

class Defer(Node):
    expr: Expression

class Select(Node):
    cases: List['SelectCase']

class SelectCase(Node):
    body: List['Statement']
    expr: Optional[Union['Send', 'SelectReceive']]

class SelectReceive(Node):
    svd   : bool
    value : Expression
    terms : List[Union[Name, Expression]]

class Switch(Node):
    expr  : Optional[Expression]
    init  : Optional['SimpleStatement']
    cases : List['SwitchCase']

class SwitchCase(Node):
    vals: List[Expression]
    body: List['Statement']

class TypeSwitch(Node):
    name  : Optional[Name]
    type  : Optional[Primary]
    init  : Optional['SimpleStatement']
    cases : List['TypeSwitchCase']

class TypeSwitchCase(Node):
    body  : List['Statement']
    types : List[Type]

### Statements -- Control Flow Transfers ###

class Goto(Node):
    label: Name

class Label(Node):
    name: Name
    body: 'Statement'

class Return(Node):
    vals: List[Expression]

class Break(Node):
    label: Optional[Name]

class Continue(Node):
    label: Optional[Name]

class Fallthrough(Node):
    pass

### Statements -- Simple Statements ###

class Send(Node):
    chan: Expression
    expr: Expression

class Empty(Node):
    pass

class IncDec(Node):
    incr: bool
    expr: Expression

class Assignment(Node):
    type: Operator
    lval: List[Expression]
    rval: List[Expression]

SimpleStatement = Union[
    Send,
    Empty,
    IncDec,
    InitSpec,
    Assignment,
    Expression,
]

### Statements -- Generic Statements ###

class CompoundStatement(Node):
    body: List['Statement']

Statement = Union[
    Go,
    If,
    For,
    Goto,
    Break,
    Defer,
    Label,
    Switch,
    Select,
    Return,
    ForRange,
    Continue,
    TypeSwitch,
    Fallthrough,
    List[InitSpec],
    List[TypeSpec],
    SimpleStatement,
    CompoundStatement,
]
