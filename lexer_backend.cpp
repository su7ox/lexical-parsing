#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <cctype>
#include <algorithm>

// ── Token Types ────────────────────────────────────────────────────────────
enum TokenType {
    TOK_KEYWORD,
    TOK_IDENTIFIER,
    TOK_INTEGER,
    TOK_FLOAT,
    TOK_STRING,
    TOK_CHAR,
    TOK_OPERATOR,
    TOK_PUNCTUATION,
    TOK_PREPROCESSOR,
    TOK_COMMENT,
    TOK_UNKNOWN
};

std::string tokenTypeName(TokenType t) {
    switch (t) {
        case TOK_KEYWORD:      return "KEYWORD";
        case TOK_IDENTIFIER:   return "IDENTIFIER";
        case TOK_INTEGER:      return "INTEGER_LITERAL";
        case TOK_FLOAT:        return "FLOAT_LITERAL";
        case TOK_STRING:       return "STRING_LITERAL";
        case TOK_CHAR:         return "CHAR_LITERAL";
        case TOK_OPERATOR:     return "OPERATOR";
        case TOK_PUNCTUATION:  return "PUNCTUATION";
        case TOK_PREPROCESSOR: return "PREPROCESSOR";
        case TOK_COMMENT:      return "COMMENT";
        default:               return "UNKNOWN";
    }
}

// ── C++ Keywords ───────────────────────────────────────────────────────────
const std::unordered_set<std::string> KEYWORDS = {
    "alignas","alignof","and","and_eq","asm","auto","bitand","bitor",
    "bool","break","case","catch","char","char8_t","char16_t","char32_t",
    "class","compl","concept","const","consteval","constexpr","constinit",
    "const_cast","continue","co_await","co_return","co_yield","decltype",
    "default","delete","do","double","dynamic_cast","else","enum","explicit",
    "export","extern","false","float","for","friend","goto","if","inline",
    "int","long","mutable","namespace","new","noexcept","not","not_eq",
    "nullptr","operator","or","or_eq","private","protected","public",
    "register","reinterpret_cast","requires","return","short","signed",
    "sizeof","static","static_assert","static_cast","struct","switch",
    "template","this","thread_local","throw","true","try","typedef",
    "typeid","typename","union","unsigned","using","virtual","void",
    "volatile","wchar_t","while","xor","xor_eq","override","final",
    "import","module","string","vector","map","set","pair","cout",
    "cin","endl","std","include","define","ifdef","ifndef","endif",
    "pragma","NULL","size_t","uint8_t","uint16_t","uint32_t","uint64_t",
    "int8_t","int16_t","int32_t","int64_t"
};

// ── Multi-char Operators (longest-match) ──────────────────────────────────
const std::vector<std::string> MULTI_OPS = {
    "<<=",">>="  ,
    "->*",".*"  ,
    "<<" ,">>"  ,
    "<=" ,">="  ,
    "==" ,"!="  ,
    "&&" ,"||"  ,
    "++" ,"--"  ,
    "+=" ,"-="  ,
    "*=" ,"/="  ,
    "%=" ,"&="  ,
    "|=" ,"^="  ,
    "->" ,"::"  ,
    "..." 
};

// ── Token Struct ───────────────────────────────────────────────────────────
struct Token {
    TokenType   type;
    std::string value;
    int         line;
    int         col;
};

// ── Symbol Table Entry ─────────────────────────────────────────────────────
struct SymbolEntry {
    std::string name;
    std::string category;      // variable / function / type / unknown
    int         firstLine;
    int         occurrences;
    std::vector<int> lines;
};

// ── Escape a string for JSON ───────────────────────────────────────────────
std::string jsonEscape(const std::string& s) {
    std::string out;
    out.reserve(s.size());
    for (unsigned char c : s) {
        switch (c) {
            case '"':  out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n";  break;
            case '\r': out += "\\r";  break;
            case '\t': out += "\\t";  break;
            default:
                if (c < 0x20) {
                    char buf[8];
                    snprintf(buf, sizeof(buf), "\\u%04x", c);
                    out += buf;
                } else {
                    out += c;
                }
        }
    }
    return out;
}

// ══════════════════════════════════════════════════════════════════════════
//  Lexer
// ══════════════════════════════════════════════════════════════════════════
class Lexer {
public:
    std::vector<Token>   tokens;
    std::unordered_map<std::string, SymbolEntry> symTable;

    void analyze(const std::string& src) {
        size_t i   = 0;
        int    line = 1;
        int    col  = 1;
        size_t n   = src.size();

        while (i < n) {
            char c = src[i];

            // ── Newline ─────────────────────────────────────────────────
            if (c == '\n') { ++line; col = 1; ++i; continue; }
            if (c == '\r') { ++i; continue; }
            if (std::isspace((unsigned char)c)) { ++col; ++i; continue; }

            int startLine = line;
            int startCol  = col;

            // ── Preprocessor directive ───────────────────────────────────
            if (c == '#') {
                std::string tok;
                tok += c; ++i; ++col;
                while (i < n && src[i] != '\n') {
                    // handle line-continuation
                    if (src[i] == '\\' && i+1 < n && src[i+1] == '\n') {
                        tok += '\n'; i += 2; ++line; col = 1;
                    } else {
                        tok += src[i]; ++i; ++col;
                    }
                }
                addToken(TOK_PREPROCESSOR, tok, startLine, startCol);
                continue;
            }

            // ── Line comment  //... ──────────────────────────────────────
            if (c == '/' && i+1 < n && src[i+1] == '/') {
                std::string tok;
                while (i < n && src[i] != '\n') { tok += src[i]; ++i; ++col; }
                addToken(TOK_COMMENT, tok, startLine, startCol);
                continue;
            }

            // ── Block comment  /* ... */ ─────────────────────────────────
            if (c == '/' && i+1 < n && src[i+1] == '*') {
                std::string tok;
                tok += src[i]; tok += src[i+1]; i += 2; col += 2;
                while (i < n) {
                    if (src[i] == '\n') { tok += '\n'; ++line; col = 1; ++i; }
                    else if (src[i] == '*' && i+1 < n && src[i+1] == '/') {
                        tok += "*/"; i += 2; col += 2; break;
                    } else { tok += src[i]; ++i; ++col; }
                }
                addToken(TOK_COMMENT, tok, startLine, startCol);
                continue;
            }

            // ── String literal ───────────────────────────────────────────
            if (c == '"') {
                std::string tok;
                tok += c; ++i; ++col;
                while (i < n && src[i] != '"') {
                    if (src[i] == '\\' && i+1 < n) {
                        tok += src[i]; tok += src[i+1];
                        if (src[i+1] == '\n') { ++line; col = 1; } else col += 2;
                        i += 2;
                    } else {
                        if (src[i] == '\n') { ++line; col = 1; }
                        tok += src[i]; ++i; ++col;
                    }
                }
                if (i < n) { tok += '"'; ++i; ++col; }
                addToken(TOK_STRING, tok, startLine, startCol);
                continue;
            }

            // ── Raw string  R"(...)" ─────────────────────────────────────
            if (c == 'R' && i+1 < n && src[i+1] == '"') {
                std::string tok;
                tok += c; tok += src[i+1]; i += 2; col += 2;
                // find delimiter
                std::string delim;
                while (i < n && src[i] != '(') { delim += src[i]; tok += src[i]; ++i; ++col; }
                if (i < n) { tok += '('; ++i; ++col; }
                std::string closing = ")" + delim + "\"";
                while (i < n) {
                    if (src.substr(i, closing.size()) == closing) {
                        tok += closing; i += closing.size(); col += (int)closing.size(); break;
                    }
                    if (src[i] == '\n') { ++line; col = 1; }
                    tok += src[i]; ++i; ++col;
                }
                addToken(TOK_STRING, tok, startLine, startCol);
                continue;
            }

            // ── Char literal ─────────────────────────────────────────────
            if (c == '\'') {
                std::string tok;
                tok += c; ++i; ++col;
                while (i < n && src[i] != '\'') {
                    if (src[i] == '\\' && i+1 < n) {
                        tok += src[i]; tok += src[i+1]; i += 2; col += 2;
                    } else { tok += src[i]; ++i; ++col; }
                }
                if (i < n) { tok += '\''; ++i; ++col; }
                addToken(TOK_CHAR, tok, startLine, startCol);
                continue;
            }

            // ── Number literal ───────────────────────────────────────────
            if (std::isdigit((unsigned char)c) ||
                (c == '.' && i+1 < n && std::isdigit((unsigned char)src[i+1]))) {
                std::string tok;
                bool isFloat = false;
                // hex / binary / octal prefix
                if (c == '0' && i+1 < n && (src[i+1] == 'x' || src[i+1] == 'X')) {
                    tok += src[i]; tok += src[i+1]; i += 2; col += 2;
                    while (i < n && std::isxdigit((unsigned char)src[i])) { tok += src[i]; ++i; ++col; }
                } else if (c == '0' && i+1 < n && (src[i+1] == 'b' || src[i+1] == 'B')) {
                    tok += src[i]; tok += src[i+1]; i += 2; col += 2;
                    while (i < n && (src[i] == '0' || src[i] == '1')) { tok += src[i]; ++i; ++col; }
                } else {
                    while (i < n && (std::isdigit((unsigned char)src[i]) || src[i] == '\'')) {
                        if (src[i] != '\'') tok += src[i]; ++i; ++col;
                    }
                    if (i < n && src[i] == '.') { isFloat = true; tok += src[i]; ++i; ++col;
                        while (i < n && std::isdigit((unsigned char)src[i])) { tok += src[i]; ++i; ++col; }
                    }
                    if (i < n && (src[i] == 'e' || src[i] == 'E')) { isFloat = true; tok += src[i]; ++i; ++col;
                        if (i < n && (src[i] == '+' || src[i] == '-')) { tok += src[i]; ++i; ++col; }
                        while (i < n && std::isdigit((unsigned char)src[i])) { tok += src[i]; ++i; ++col; }
                    }
                }
                // suffixes (u, l, f, ul, ll ...)
                while (i < n && (src[i] == 'u' || src[i] == 'U' || src[i] == 'l' || src[i] == 'L' || src[i] == 'f' || src[i] == 'F')) {
                    if (src[i] == 'f' || src[i] == 'F') isFloat = true;
                    tok += src[i]; ++i; ++col;
                }
                addToken(isFloat ? TOK_FLOAT : TOK_INTEGER, tok, startLine, startCol);
                continue;
            }

            // ── Identifier / Keyword ─────────────────────────────────────
            if (std::isalpha((unsigned char)c) || c == '_') {
                std::string tok;
                while (i < n && (std::isalnum((unsigned char)src[i]) || src[i] == '_')) {
                    tok += src[i]; ++i; ++col;
                }
                bool isKw = KEYWORDS.count(tok) > 0;
                addToken(isKw ? TOK_KEYWORD : TOK_IDENTIFIER, tok, startLine, startCol);
                if (!isKw) updateSymbol(tok, startLine, src, i);
                continue;
            }

            // ── Multi-char operators (longest match) ─────────────────────
            {
                bool found = false;
                for (const auto& op : MULTI_OPS) {
                    if (src.substr(i, op.size()) == op) {
                        addToken(TOK_OPERATOR, op, startLine, startCol);
                        col += (int)op.size(); i += op.size();
                        found = true; break;
                    }
                }
                if (found) continue;
            }

            // ── Single-char operator / punctuation ───────────────────────
            {
                const std::string OPS    = "+-*/%=<>!&|^~?";
                const std::string PUNCTS = "(){}[];:,.'";
                if (OPS.find(c) != std::string::npos) {
                    addToken(TOK_OPERATOR, std::string(1, c), startLine, startCol);
                } else if (PUNCTS.find(c) != std::string::npos) {
                    addToken(TOK_PUNCTUATION, std::string(1, c), startLine, startCol);
                } else {
                    addToken(TOK_UNKNOWN, std::string(1, c), startLine, startCol);
                }
                ++i; ++col;
                continue;
            }
        }
    }

private:
    void addToken(TokenType t, const std::string& val, int line, int col) {
        tokens.push_back({t, val, line, col});
    }

    // Heuristic: peek ahead to guess identifier role
    void updateSymbol(const std::string& name, int line,
                      const std::string& src, size_t pos) {
        // skip whitespace
        size_t p = pos;
        while (p < src.size() && std::isspace((unsigned char)src[p])) ++p;

        std::string cat = "variable";
        if (p < src.size() && src[p] == '(') cat = "function";
        else if (p < src.size() && src[p] == '<') cat = "template/type";

        // check if previous token looks like a type keyword (crude)
        if (!tokens.empty()) {
            auto& prev = tokens[tokens.size() - 1]; // the identifier itself
            // look one more back
            if (tokens.size() >= 2) {
                auto& before = tokens[tokens.size() - 2];
                if (before.type == TOK_KEYWORD) {
                    static const std::unordered_set<std::string> TYPE_KWS = {
                        "int","long","short","char","bool","float","double",
                        "void","auto","unsigned","signed","const","wchar_t",
                        "string","vector","map","set"
                    };
                    if (TYPE_KWS.count(before.value)) {
                        if (cat != "function") cat = "variable";
                    }
                    if (before.value == "class" || before.value == "struct" ||
                        before.value == "enum"  || before.value == "union"  ||
                        before.value == "typedef") {
                        cat = "type";
                    }
                    if (before.value == "namespace") cat = "namespace";
                }
            }
        }

        auto it = symTable.find(name);
        if (it == symTable.end()) {
            symTable[name] = {name, cat, line, 1, {line}};
        } else {
            it->second.occurrences++;
            it->second.lines.push_back(line);
        }
    }
};

// ══════════════════════════════════════════════════════════════════════════
//  JSON Output
// ══════════════════════════════════════════════════════════════════════════
void outputJSON(const Lexer& lex) {
    std::cout << "{\n";

    // ── tokens ─────────────────────────────────────────────────────────
    std::cout << "  \"tokens\": [\n";
    for (size_t i = 0; i < lex.tokens.size(); ++i) {
        const auto& t = lex.tokens[i];
        std::cout << "    {"
                  << "\"type\": \""  << tokenTypeName(t.type) << "\", "
                  << "\"value\": \"" << jsonEscape(t.value)   << "\", "
                  << "\"line\": "    << t.line                << ", "
                  << "\"col\": "     << t.col
                  << "}";
        if (i + 1 < lex.tokens.size()) std::cout << ",";
        std::cout << "\n";
    }
    std::cout << "  ],\n";

    // ── symbol_table ────────────────────────────────────────────────────
    std::cout << "  \"symbol_table\": [\n";
    std::vector<SymbolEntry> syms;
    syms.reserve(lex.symTable.size());
    for (const auto& kv : lex.symTable) syms.push_back(kv.second);
    std::sort(syms.begin(), syms.end(),
              [](const SymbolEntry& a, const SymbolEntry& b) {
                  return a.firstLine < b.firstLine;
              });

    for (size_t i = 0; i < syms.size(); ++i) {
        const auto& s = syms[i];
        std::cout << "    {"
                  << "\"name\": \""       << jsonEscape(s.name)     << "\", "
                  << "\"category\": \""   << s.category             << "\", "
                  << "\"first_line\": "   << s.firstLine            << ", "
                  << "\"occurrences\": "  << s.occurrences          << ", "
                  << "\"lines\": [";
        for (size_t j = 0; j < s.lines.size(); ++j) {
            std::cout << s.lines[j];
            if (j + 1 < s.lines.size()) std::cout << ", ";
        }
        std::cout << "]}";
        if (i + 1 < syms.size()) std::cout << ",";
        std::cout << "\n";
    }
    std::cout << "  ]\n";
    std::cout << "}\n";
}

// ══════════════════════════════════════════════════════════════════════════
int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "{\"error\": \"Usage: lexer <source.cpp>\"}\n";
        return 1;
    }

    std::ifstream f(argv[1]);
    if (!f) {
        std::cerr << "{\"error\": \"Cannot open file: " << argv[1] << "\"}\n";
        return 1;
    }

    std::ostringstream ss;
    ss << f.rdbuf();
    std::string src = ss.str();

    Lexer lex;
    lex.analyze(src);
    outputJSON(lex);
    return 0;
}
