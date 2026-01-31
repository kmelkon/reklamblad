import js from '@eslint/js';
import globals from 'globals';

export default [
    js.configs.recommended,
    {
        ignores: ['eslint.config.js'],
    },
    {
        files: ['**/*.js'],
        ignores: ['eslint.config.js', 'node_modules/**', 'venv/**', '.venv/**'],
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: 'script',
            globals: {
                ...globals.browser,
                // Cross-file globals (writable since defined in one file, used in others)
                Utils: 'writable',
                Router: 'writable',
                router: 'writable',
                RecipeApp: 'writable',
                DealsApp: 'writable',
                dealsApp: 'writable',
                ListsApp: 'writable',
                listsApp: 'writable',
            },
        },
        rules: {
            'no-unused-vars': ['error', {
                argsIgnorePattern: '^_',
                varsIgnorePattern: '^(Utils|Router|router|RecipeApp|DealsApp|dealsApp|ListsApp|listsApp)$',
            }],
            'no-undef': 'error',
            'no-redeclare': ['error', { builtinGlobals: false }],
            'eqeqeq': ['error', 'always'],
            'no-var': 'error',
            'prefer-const': 'error',
        },
    },
];
