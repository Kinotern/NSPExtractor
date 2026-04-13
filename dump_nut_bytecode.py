import argparse
import json
import struct
from pathlib import Path

TYPE_NULL = 0x01 | 0x01000000
TYPE_STRING = 0x10 | 0x08000000
TYPE_INTEGER = 0x02 | 0x04000000 | 0x01000000
TYPE_FLOAT = 0x04 | 0x04000000 | 0x01000000

OPCODE_NAMES = [
    "OP_LINE", "OP_LOAD", "OP_LOADINT", "OP_LOADFLOAT", "OP_DLOAD",
    "OP_TAILCALL", "OP_CALL", "OP_PREPCALL", "OP_PREPCALLK", "OP_GETK",
    "OP_MOVE", "OP_NEWSLOT", "OP_DELETE", "OP_SET", "OP_GET",
    "OP_EQ", "OP_NE", "OP_ARITH", "OP_BITW", "OP_RETURN",
    "OP_LOADNULLS", "OP_LOADROOTTABLE", "OP_LOADBOOL", "OP_DMOVE", "OP_JMP",
    "OP_JNZ", "OP_JZ", "OP_LOADFREEVAR", "OP_VARGC", "OP_GETVARGV",
    "OP_NEWTABLE", "OP_NEWARRAY", "OP_APPENDARRAY", "OP_GETPARENT",
    "OP_COMPARITH", "OP_COMPARITHL", "OP_INC", "OP_INCL", "OP_PINC",
    "OP_PINCL", "OP_CMP", "OP_EXISTS", "OP_INSTANCEOF", "OP_AND",
    "OP_OR", "OP_NEG", "OP_NOT", "OP_BWNOT", "OP_CLOSURE",
    "OP_YIELD", "OP_RESUME", "OP_FOREACH", "OP_POSTFOREACH", "OP_DELEGATE",
    "OP_CLONE", "OP_TYPEOF", "OP_PUSHTRAP", "OP_POPTRAP", "OP_THROW",
    "OP_CLASS", "OP_NEWSLOTA",
]


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.off = 0

    def read(self, n: int) -> bytes:
        b = self.data[self.off:self.off + n]
        if len(b) != n:
            raise EOFError("unexpected eof")
        self.off += n
        return b

    def u16(self) -> int:
        return struct.unpack_from("<H", self.read(2))[0]

    def i32(self) -> int:
        return struct.unpack_from("<i", self.read(4))[0]

    def u32(self) -> int:
        return struct.unpack_from("<I", self.read(4))[0]

    def i64(self) -> int:
        return struct.unpack_from("<q", self.read(8))[0]

    def u64(self) -> int:
        return struct.unpack_from("<Q", self.read(8))[0]

    def f32(self) -> float:
        return struct.unpack_from("<f", self.read(4))[0]

    def bool(self) -> bool:
        return self.read(1) != b"\x00"

    def sq_string(self) -> str:
        length = self.u64()
        return self.read(length).decode("utf-8", errors="replace")

    def sq_string32(self) -> str:
        length = self.u32()
        return self.read(length).decode("utf-8", errors="replace")

    def sq_string_object(self) -> str:
        ty = self.i32()
        if ty == TYPE_STRING:
            return self.sq_string()
        if ty == TYPE_NULL:
            return ""
        raise ValueError(f"expected string object, got 0x{ty:08x}")

    def sq_string_object32(self) -> str:
        ty = self.i32()
        if ty == TYPE_STRING:
            return self.sq_string32()
        if ty == TYPE_NULL:
            return ""
        raise ValueError(f"expected string object, got 0x{ty:08x}")

    def confirm_part(self) -> None:
        if self.read(8) != b"PART\x00\x00\x00\x00":
            raise ValueError("bad PART marker")

    def confirm_part32(self) -> None:
        if self.read(4) != b"TRAP":
            raise ValueError("bad PART marker")


def load_sq_object(r: Reader):
    ty = r.i32()
    if ty == TYPE_NULL:
        return None
    if ty == TYPE_STRING:
        return r.sq_string()
    if ty == TYPE_INTEGER:
        return r.u32()
    if ty == TYPE_FLOAT:
        return r.f32()
    raise ValueError(f"unknown sq object type 0x{ty:08x}")


def load_sq_object32(r: Reader):
    ty = r.i32()
    if ty == TYPE_NULL:
        return None
    if ty == TYPE_STRING:
        return r.sq_string32()
    if ty == TYPE_INTEGER:
        return r.u32()
    if ty == TYPE_FLOAT:
        return r.f32()
    raise ValueError(f"unknown sq object type 0x{ty:08x}")


def load_function(r: Reader):
    r.confirm_part()
    source_name = r.sq_string_object()
    name = r.sq_string_object()
    r.confirm_part()
    n_literals = r.i64()
    n_params = r.i64()
    n_outer = r.i64()
    n_locals = r.i64()
    n_lines = r.i64()
    n_defaults = r.i64()
    n_instr = r.i64()
    n_funcs = r.i64()
    r.confirm_part()
    literals = [load_sq_object(r) for _ in range(n_literals)]
    r.confirm_part()
    params = [r.sq_string_object() for _ in range(n_params)]
    r.confirm_part()
    outer_values = []
    for _ in range(n_outer):
        outer_values.append({"type": r.i32(), "src": load_sq_object(r), "name": load_sq_object(r)})
    r.confirm_part()
    locals_ = []
    for _ in range(n_locals):
        locals_.append({"name": r.sq_string_object(), "pos": r.i64(), "start_op": r.i64(), "end_op": r.i64()})
    r.confirm_part()
    line_infos = [{"line": r.i64(), "op": r.i64()} for _ in range(n_lines)]
    r.confirm_part()
    default_params = [r.i32() for _ in range(n_defaults)]
    r.confirm_part()
    instructions = []
    for _ in range(n_instr):
        arg1 = r.i32()
        op, arg0, arg2, arg3 = struct.unpack("<bbbb", r.read(4))
        instructions.append({
            "op": op & 0xFF,
            "name": OPCODE_NAMES[op & 0xFF] if (op & 0xFF) < len(OPCODE_NAMES) else f"OP_{op & 0xFF}",
            "arg0": arg0, "arg1": arg1,
            "arg1_float": struct.unpack("<f", struct.pack("<i", arg1))[0],
            "arg2": arg2, "arg3": arg3,
        })
    r.confirm_part()
    functions = [load_function(r) for _ in range(n_funcs)]
    stack_size = r.i64()
    is_generator = r.bool()
    got_var_params = r.bool()
    return {
        "source_name": source_name, "name": name, "literals": literals,
        "parameters": params, "outer_values": outer_values, "locals": locals_,
        "line_infos": line_infos, "default_params": default_params,
        "instructions": instructions, "functions": functions,
        "stack_size": stack_size, "is_generator": is_generator, "got_var_params": got_var_params,
    }


def load_function32(r: Reader):
    r.confirm_part32()
    source_name = r.sq_string_object32()
    name = r.sq_string_object32()
    r.confirm_part32()
    n_literals = r.i32()
    n_params = r.i32()
    n_outer = r.i32()
    n_locals = r.i32()
    n_lines = r.i32()
    n_defaults = r.i32()
    n_instr = r.i32()
    n_funcs = r.i32()
    r.confirm_part32()
    literals = [load_sq_object32(r) for _ in range(n_literals)]
    r.confirm_part32()
    params = [r.sq_string_object32() for _ in range(n_params)]
    r.confirm_part32()
    outer_values = []
    for _ in range(n_outer):
        outer_values.append({"type": r.i32(), "src": load_sq_object32(r), "name": load_sq_object32(r)})
    r.confirm_part32()
    locals_ = []
    for _ in range(n_locals):
        locals_.append({"name": r.sq_string_object32(), "pos": r.i32(), "start_op": r.i32(), "end_op": r.i32()})
    r.confirm_part32()
    line_infos = [{"line": r.i32(), "op": r.i32()} for _ in range(n_lines)]
    r.confirm_part32()
    default_params = [r.i32() for _ in range(n_defaults)]
    r.confirm_part32()
    instructions = []
    for _ in range(n_instr):
        arg1 = r.i32()
        op, arg0, arg2, arg3 = struct.unpack("<bbbb", r.read(4))
        instructions.append({
            "op": op & 0xFF,
            "name": OPCODE_NAMES[op & 0xFF] if (op & 0xFF) < len(OPCODE_NAMES) else f"OP_{op & 0xFF}",
            "arg0": arg0, "arg1": arg1,
            "arg1_float": struct.unpack("<f", struct.pack("<i", arg1))[0],
            "arg2": arg2, "arg3": arg3,
        })
    r.confirm_part32()
    functions = [load_function32(r) for _ in range(n_funcs)]
    stack_size = r.i32()
    is_generator = r.bool()
    got_var_params = r.bool()
    return {
        "source_name": source_name, "name": name, "literals": literals,
        "parameters": params, "outer_values": outer_values, "locals": locals_,
        "line_infos": line_infos, "default_params": default_params,
        "instructions": instructions, "functions": functions,
        "stack_size": stack_size, "is_generator": is_generator, "got_var_params": got_var_params,
    }


def parse_script(path: Path):
    r = Reader(path.read_bytes())
    if r.u16() != 0xFAFA:
        raise ValueError("bad magic")
    sig = r.read(4)
    if sig != b"RIQS":
        raise ValueError("bad SQIR header")
    v_or_char = r.u32()
    if v_or_char == 1:
        main = load_function32(r)
        if r.read(4) != b"LIAT":
            raise ValueError("missing TAIL")
    else:
        if r.read(4) != b"\x00\x00\x00\x00":
            raise ValueError("unexpected legacy header")
        if r.u64() != 1:
            raise ValueError("unexpected char size")
        main = load_function(r)
        if r.read(8) != b"TAIL\x00\x00\x00\x00":
            raise ValueError("missing TAIL")
    return main


def format_instruction(idx: int, ins: dict, literals: list) -> str:
    name = ins["name"]
    base = f"[{idx:03d}] {name:<14} {ins['arg0']:>4} "
    if name == "OP_LOAD" and 0 <= ins["arg1"] < len(literals):
        return base + repr(literals[ins["arg1"]])
    if name == "OP_DLOAD":
        a = literals[ins["arg1"]] if 0 <= ins["arg1"] < len(literals) else ins["arg1"]
        b = literals[ins["arg3"] & 0xFF] if 0 <= (ins["arg3"] & 0xFF) < len(literals) else ins["arg3"]
        return base + f"{a!r} {ins['arg2']:>4} {b!r}"
    if name == "OP_LOADINT":
        return base + str(ins["arg1"])
    if name == "OP_LOADFLOAT":
        return base + str(ins["arg1_float"])
    if name == "OP_LOADBOOL":
        return base + ("true" if ins["arg1"] else "false")
    if name in ("OP_PREPCALLK", "OP_GETK") and 0 <= ins["arg1"] < len(literals):
        lit = literals[ins["arg1"]]
        return base + f"({ins['arg2']}).{lit} {ins['arg3']}"
    if name == "OP_ARITH":
        return base + f"[{chr(ins['arg3'] & 0xFF)}] {ins['arg1']} {ins['arg2']}"
    return base + f"{ins['arg1']:>6} {ins['arg2']:>4} {ins['arg3']:>4}"


def dump_function(fn: dict, out_lines: list, depth: int = 0):
    prefix = "  " * depth
    out_lines.append(f"{prefix}Function: {fn['name'] or '<anonymous>'}")
    out_lines.append(f"{prefix}Source: {fn['source_name']}")
    out_lines.append(f"{prefix}Params: {', '.join(fn['parameters']) if fn['parameters'] else '-'}")
    out_lines.append(f"{prefix}Locals: {len(fn['locals'])}  Literals: {len(fn['literals'])}  Instructions: {len(fn['instructions'])}")
    if fn["literals"]:
        out_lines.append(f"{prefix}Literals:")
        for i, lit in enumerate(fn["literals"]):
            out_lines.append(f"{prefix}  [{i}] {lit!r}")
    if fn["locals"]:
        out_lines.append(f"{prefix}LocalVars:")
        for loc in fn["locals"]:
            out_lines.append(f"{prefix}  {loc['name']} pos={loc['pos']} start={loc['start_op']} end={loc['end_op']}")
    out_lines.append(f"{prefix}Instructions:")
    for i, ins in enumerate(fn["instructions"]):
        out_lines.append(prefix + "  " + format_instruction(i, ins, fn["literals"]))
    for sub in fn["functions"]:
        out_lines.append("")
        dump_function(sub, out_lines, depth + 1)


def main():
    parser = argparse.ArgumentParser(description="Dump Squirrel bytecode (.nut.m / SQIR) to readable text/json.")
    parser.add_argument("input", help="Input .nut.m file")
    parser.add_argument("-o", "--output", help="Output text path")
    parser.add_argument("--json", dest="json_output", help="Optional JSON output path")
    args = parser.parse_args()

    src = Path(args.input).resolve()
    fn = parse_script(src)

    lines = []
    dump_function(fn, lines)
    text = "\n".join(lines) + "\n"

    out_path = Path(args.output).resolve() if args.output else src.with_suffix(src.suffix + ".txt")
    out_path.write_text(text, encoding="utf-8")

    if args.json_output:
        Path(args.json_output).resolve().write_text(
            json.dumps(fn, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(out_path)


if __name__ == "__main__":
    main()
