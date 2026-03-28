#include <iostream>
#include <fstream>
#include <sstream>
#include <algorithm>
#include "lexer.h"
#include "parser.h"

// ── Escape a string for JSON ──
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

// ── JSON Output ──
void outputJSON(const Lexer& lex) {
    std::cout << "{\n";

    // Tokens
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

    // Symbol Table
    std::cout << "  \"symbol_table\": [\n";
    std::vector<SymbolEntry> syms;
    for (const auto& kv : lex.symTable) syms.push_back(kv.second);
    std::sort(syms.begin(), syms.end(), [](const SymbolEntry& a, const SymbolEntry& b) {
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
    
    // Abstract Syntax Tree (NEW)
    std::cout << "  ],\n";  // Notice the crucial comma added here!
    Parser parser(lex.tokens);
    std::cout << "  \"ast\": " << parser.parseProgram() << "\n";
    std::cout << "}\n";
}

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