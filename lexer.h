#ifndef LEXER_H
#define LEXER_H

#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <cctype>

enum TokenType {
    TOK_KEYWORD, TOK_IDENTIFIER, TOK_INTEGER, TOK_FLOAT,
    TOK_STRING, TOK_CHAR, TOK_OPERATOR, TOK_PUNCTUATION,
    TOK_PREPROCESSOR, TOK_COMMENT, TOK_UNKNOWN
};

inline std::string tokenTypeName(TokenType t) {
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

struct Token {
    TokenType   type;
    std::string value;
    int         line;
    int         col;
};

struct SymbolEntry {
    std::string name;
    std::string category;
    int         firstLine;
    int         occurrences;
    std::vector<int> lines;
};

class Lexer {
public:
    std::vector<Token> tokens;
    std::unordered_map<std::string, SymbolEntry> symTable;

    void analyze(const std::string& src) {
        const std::unordered_set<std::string> KEYWORDS = {
            "int", "long", "short", "char", "bool", "float", "double", "void",
            "auto", "unsigned", "signed", "const", "class", "struct", "return",
            "if", "else", "while", "for", "namespace", "using", "std", "cout", "endl"
        };
        const std::vector<std::string> MULTI_OPS = {
            "<<=", ">>=", "->*", ".*", "<<", ">>", "<=", ">=", "==", "!=",
            "&&", "||", "++", "--", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "->", "::"
        };

        size_t i = 0;
        int line = 1, col = 1;
        size_t n = src.size();

        while (i < n) {
            char c = src[i];

            if (c == '\n') { ++line; col = 1; ++i; continue; }
            if (c == '\r') { ++i; continue; }
            if (std::isspace((unsigned char)c)) { ++col; ++i; continue; }

            int startLine = line, startCol = col;

            // Preprocessor
            if (c == '#') {
                std::string tok(1, c); ++i; ++col;
                while (i < n && src[i] != '\n') { tok += src[i]; ++i; ++col; }
                addToken(TOK_PREPROCESSOR, tok, startLine, startCol);
                continue;
            }

            // Line Comment
            if (c == '/' && i + 1 < n && src[i + 1] == '/') {
                std::string tok;
                while (i < n && src[i] != '\n') { tok += src[i]; ++i; ++col; }
                addToken(TOK_COMMENT, tok, startLine, startCol);
                continue;
            }

            // String Literal
            if (c == '"') {
                std::string tok(1, c); ++i; ++col;
                while (i < n && src[i] != '"') {
                    if (src[i] == '\\' && i + 1 < n) { tok += src[i]; tok += src[i + 1]; i += 2; col += 2; }
                    else { tok += src[i]; ++i; ++col; }
                }
                if (i < n) { tok += '"'; ++i; ++col; }
                addToken(TOK_STRING, tok, startLine, startCol);
                continue;
            }

            // Numbers
            if (std::isdigit((unsigned char)c)) {
                std::string tok;
                bool isFloat = false;
                while (i < n && (std::isdigit((unsigned char)src[i]) || src[i] == '.')) {
                    if (src[i] == '.') isFloat = true;
                    tok += src[i]; ++i; ++col;
                }
                addToken(isFloat ? TOK_FLOAT : TOK_INTEGER, tok, startLine, startCol);
                continue;
            }

            // Identifiers & Keywords
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

            // Multi-char Operators
            bool foundMulti = false;
            for (const auto& op : MULTI_OPS) {
                if (src.substr(i, op.size()) == op) {
                    addToken(TOK_OPERATOR, op, startLine, startCol);
                    col += op.size(); i += op.size();
                    foundMulti = true; break;
                }
            }
            if (foundMulti) continue;

            // Single char operators / punctuation
            const std::string OPS = "+-*/%=<>!&|^~?";
            const std::string PUNCTS = "(){}[];:,.'";
            if (OPS.find(c) != std::string::npos) {
                addToken(TOK_OPERATOR, std::string(1, c), startLine, startCol);
            } else if (PUNCTS.find(c) != std::string::npos) {
                addToken(TOK_PUNCTUATION, std::string(1, c), startLine, startCol);
            } else {
                addToken(TOK_UNKNOWN, std::string(1, c), startLine, startCol);
            }
            ++i; ++col;
        }
    }

private:
    void addToken(TokenType t, const std::string& val, int line, int col) {
        tokens.push_back({t, val, line, col});
    }

    void updateSymbol(const std::string& name, int line, const std::string& src, size_t pos) {
        size_t p = pos;
        while (p < src.size() && std::isspace((unsigned char)src[p])) ++p;
        std::string cat = (p < src.size() && src[p] == '(') ? "function" : "variable";
        
        auto it = symTable.find(name);
        if (it == symTable.end()) {
            symTable[name] = {name, cat, line, 1, {line}};
        } else {
            it->second.occurrences++;
            it->second.lines.push_back(line);
        }
    }
};

#endif