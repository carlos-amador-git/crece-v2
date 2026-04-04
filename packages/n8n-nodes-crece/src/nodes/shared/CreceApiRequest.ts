import type {
	IExecuteFunctions,
	IHttpRequestMethods,
	IHttpRequestOptions,
} from 'n8n-workflow';

/**
 * Shared helper for making authenticated requests to the CRECE v2.0 API.
 *
 * Retrieves the `creceApi` credentials from the node context, constructs
 * the full URL from the configured base + endpoint, and attaches the JWT
 * bearer token to the Authorization header.
 *
 * @param method  - HTTP method (GET, POST, PATCH, PUT, DELETE)
 * @param endpoint - API path relative to the base URL (e.g. "/ciudadanos/")
 * @param body    - Optional request body for POST/PATCH/PUT
 * @param query   - Optional query string parameters
 * @returns The parsed JSON response from the CRECE API
 */
export async function creceApiRequest(
	this: IExecuteFunctions,
	method: IHttpRequestMethods,
	endpoint: string,
	body?: object,
	query?: Record<string, string | number | boolean>,
): Promise<unknown> {
	const credentials = await this.getCredentials('creceApi');

	const apiUrl = (credentials.apiUrl as string).replace(/\/$/, '');
	const apiToken = credentials.apiToken as string;

	const options: IHttpRequestOptions = {
		method,
		url: `${apiUrl}${endpoint}`,
		headers: {
			Authorization: `Bearer ${apiToken}`,
			'Content-Type': 'application/json',
		},
		json: true,
	};

	if (body && Object.keys(body).length > 0) {
		options.body = body;
	}

	if (query && Object.keys(query).length > 0) {
		options.qs = query;
	}

	return this.helpers.httpRequest(options);
}
