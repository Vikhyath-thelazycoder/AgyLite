import { createServer } from 'node:http';
import { route } from './routes.js';

export const server = createServer((req, res) => route(req, res));
