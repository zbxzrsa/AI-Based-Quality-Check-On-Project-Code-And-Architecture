import js from '@eslint/js';
import globals from 'globals';
import nextPlugin from '@next/eslint-plugin-next';
import reactPlugin from 'eslint-plugin-react';
import reactHooksPlugin from 'eslint-plugin-react-hooks';
import tsParser from '@typescript-eslint/parser';
import tsPlugin from '@typescript-eslint/eslint-plugin';

export default [
    {
        ignores: [
            'node_modules/**',
            '.next/**',
            'out/**',
            'build/**',
            'dist/**',
            '.env.local',
            '.env.*.local',
        ],
    },
    js.configs.recommended,
    {
        files: ['**/*.{js,jsx,ts,tsx}'],
        languageOptions: {
            parser: tsParser,
            parserOptions: {
                ecmaVersion: 'latest',
                sourceType: 'module',
                ecmaFeatures: {
                    jsx: true,
                },
            },
            globals: {
                ...globals.browser,
                ...globals.node,
                ...globals.jest,
            },
        },
        plugins: {
            '@next/next': nextPlugin,
            react: reactPlugin,
            'react-hooks': reactHooksPlugin,
            '@typescript-eslint': tsPlugin,
        },
        settings: {
            react: {
                version: 'detect',
            },
        },
        rules: {
            ...nextPlugin.configs.recommended.rules,
            ...nextPlugin.configs['core-web-vitals'].rules,
            ...reactPlugin.configs.flat.recommended.rules,
            ...reactPlugin.configs.flat['jsx-runtime'].rules,
            ...reactHooksPlugin.configs.flat.recommended.rules,
            '@typescript-eslint/no-explicit-any': 'warn',
            'no-undef': 'off',
            'no-unused-vars': 'off',
            '@typescript-eslint/no-unused-vars': [
                'warn',
                {
                    argsIgnorePattern: '^_',
                    varsIgnorePattern: '^_',
                },
            ],
            'no-console': [
                'warn',
                {
                    allow: ['warn', 'error'],
                },
            ],
            'react/display-name': 'off',
            'react/no-unescaped-entities': 'warn',
            '@next/next/no-html-link-for-pages': 'off',
        },
    },
];
