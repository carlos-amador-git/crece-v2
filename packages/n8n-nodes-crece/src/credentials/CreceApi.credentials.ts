import {
	ICredentialType,
	INodeProperties,
	ICredentialTestRequest,
} from 'n8n-workflow';

/**
 * Credential type for authenticating with the CRECE v2.0 API.
 *
 * CRECE is a political intelligence platform that exposes a FastAPI REST API
 * secured with JWT bearer tokens.
 *
 * Environments:
 * - Local development: http://localhost:8000/api/v1
 * - Production: configured per deployment (Coolify VPS)
 */
export class CreceApi implements ICredentialType {
	name = 'creceApi';
	displayName = 'CRECE API';
	documentationUrl =
		'https://github.com/MarxCha/crece-v2/blob/main/docs/api-credentials.md';

	properties: INodeProperties[] = [
		{
			displayName: 'API URL',
			name: 'apiUrl',
			type: 'string',
			default: 'http://localhost:8000/api/v1',
			required: true,
			placeholder: 'http://localhost:8000/api/v1',
			description:
				'Base URL of the CRECE API (including /api/v1). Do not include a trailing slash.',
		},
		{
			displayName: 'API Token (JWT)',
			name: 'apiToken',
			type: 'string',
			typeOptions: {
				password: true,
			},
			default: '',
			required: true,
			placeholder: 'eyJhbGciOiJIUzI1NiIs...',
			description:
				'JWT bearer token obtained from POST /auth/login. Used in the Authorization header.',
		},
	];

	// Verify the token is valid by hitting the health or auth/me endpoint
	test: ICredentialTestRequest = {
		request: {
			baseURL: '={{$credentials.apiUrl}}',
			url: '/auth/me',
			method: 'GET',
			headers: {
				Authorization: '=Bearer {{$credentials.apiToken}}',
			},
		},
	};
}
