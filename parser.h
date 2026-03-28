#ifndef PARSER_H
#define PARSER_H

#include "lexer.h"
#include <memory>
#include <vector>
#include <string>

// --- AST Nodes ---
struct ASTNode {
    std::string type;
    virtual ~ASTNode() = default;
    virtual std::string toJson() const = 0;
};

struct NumberNode : public ASTNode {
    std::string value;
    NumberNode(std::string v) : value(v) { type = "NumberLiteral"; }
    
    std::string toJson() const override {
        return "{\"type\": \"NumberLiteral\", \"value\": \"" + value + "\"}";
    }
};

struct VarDeclNode : public ASTNode {
    std::string dataType;
    std::string identifier;
    std::unique_ptr<ASTNode> initializer;

    std::string toJson() const override {
        std::string initJson = initializer ? initializer->toJson() : "null";
        return "{\"type\": \"VarDecl\", \"dataType\": \"" + dataType + 
               "\", \"identifier\": \"" + identifier + 
               "\", \"initializer\": " + initJson + "}";
    }
};

// --- Recursive Descent Parser ---
class Parser {
    std::vector<Token> tokens;
    size_t pos = 0;

public:
    Parser(const std::vector<Token>& toks) : tokens(toks) {}

    std::string parseProgram() {
        std::string jsonStr = "[\n";
        bool first = true;

        while (pos < tokens.size()) {
            // If token is a data type, try to parse a variable declaration
            if (current().type == TOK_KEYWORD && 
               (current().value == "int" || current().value == "float" || current().value == "double")) {
                
                auto node = parseDeclaration();
                if (node) {
                    if (!first) jsonStr += ",\n";
                    jsonStr += "    " + node->toJson();
                    first = false;
                }
            } else {
                pos++; // Skip unhandled constructs (like functions, imports) for now
            }
        }
        jsonStr += "\n  ]";
        return jsonStr;
    }

private:
    Token current() {
        if (pos >= tokens.size()) return {TOK_UNKNOWN, "", -1, -1};
        return tokens[pos];
    }

    std::unique_ptr<ASTNode> parseDeclaration() {
        std::string dataType = current().value;
        pos++; // Consume 'int', 'float', etc.

        if (current().type == TOK_IDENTIFIER) {
            std::string id = current().value;
            pos++; // Consume identifier name

            std::unique_ptr<ASTNode> init = nullptr;
            
            // Check for assignment
            if (current().type == TOK_OPERATOR && current().value == "=") {
                pos++; // Consume '='
                
                if (current().type == TOK_INTEGER || current().type == TOK_FLOAT) {
                    init = std::make_unique<NumberNode>(current().value);
                    pos++; // Consume number
                }
            }

            // Consume semicolon if present
            if (current().type == TOK_PUNCTUATION && current().value == ";") {
                pos++;
            }

            auto node = std::make_unique<VarDeclNode>();
            node->dataType = dataType;
            node->identifier = id;
            node->initializer = std::move(init);
            return node;
        }
        return nullptr;
    }
};

#endif