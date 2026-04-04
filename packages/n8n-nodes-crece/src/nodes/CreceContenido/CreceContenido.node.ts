import {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
	NodeOperationError,
} from 'n8n-workflow';

import { creceApiRequest } from '../shared/CreceApiRequest';

/**
 * CRECE Contenido -- AI-powered political content generation node.
 *
 * Uses the CRECE Content Factory (Claude API + Ollama local) to generate,
 * list, and manage political content for dirigentes across platforms.
 *
 * Operations:
 * - generate:      generate new content for a dirigente
 * - list:          list existing generated content
 * - update_status: change the status of a content piece (draft, approved, published, rejected)
 */
export class CreceContenido implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'CRECE Contenido',
		name: 'creceContenido',
		icon: 'file:crece.svg',
		group: ['transform'],
		version: 1,
		subtitle: '={{$parameter["operation"]}}',
		description:
			'Generate, list, and manage AI-powered political content for dirigentes',
		defaults: {
			name: 'CRECE Contenido',
		},
		inputs: ['main'],
		outputs: ['main'],
		credentials: [
			{
				name: 'creceApi',
				required: true,
			},
		],
		properties: [
			// ------------------------------------------
			// Operation selector
			// ------------------------------------------
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				options: [
					{
						name: 'Generate',
						value: 'generate',
						description: 'Generate political content using AI',
						action: 'Generate political content',
					},
					{
						name: 'List',
						value: 'list',
						description: 'List generated content with optional filters',
						action: 'List generated content',
					},
					{
						name: 'Update Status',
						value: 'update_status',
						description: 'Change the status of a content piece',
						action: 'Update content status',
					},
				],
				default: 'generate',
			},

			// ------------------------------------------
			// Fields: Generate
			// ------------------------------------------
			{
				displayName: 'Dirigente ID',
				name: 'dirigenteId',
				type: 'string',
				default: '',
				required: true,
				displayOptions: {
					show: {
						operation: ['generate', 'list'],
					},
				},
				description: 'Internal CRECE ID of the political leader (dirigente)',
			},
			{
				displayName: 'Formato',
				name: 'formato',
				type: 'options',
				options: [
					{ name: 'Post Twitter/X', value: 'post_twitter' },
					{ name: 'Post Instagram', value: 'post_instagram' },
					{ name: 'Post Facebook', value: 'post_facebook' },
					{ name: 'Video TikTok (guion)', value: 'guion_tiktok' },
					{ name: 'Video YouTube (guion)', value: 'guion_youtube' },
					{ name: 'Comunicado de Prensa', value: 'comunicado_prensa' },
					{ name: 'Discurso', value: 'discurso' },
					{ name: 'Infografia (texto)', value: 'infografia' },
				],
				default: 'post_twitter',
				required: true,
				displayOptions: {
					show: {
						operation: ['generate'],
					},
				},
				description: 'Content format to generate',
			},
			{
				displayName: 'Tema',
				name: 'tema',
				type: 'string',
				default: '',
				required: true,
				displayOptions: {
					show: {
						operation: ['generate'],
					},
				},
				typeOptions: {
					rows: 2,
				},
				description:
					'Topic or theme for the content. Be specific for better results.',
			},
			{
				displayName: 'Tono',
				name: 'tono',
				type: 'options',
				options: [
					{ name: 'Institucional', value: 'institucional' },
					{ name: 'Cercano', value: 'cercano' },
					{ name: 'Combativo', value: 'combativo' },
					{ name: 'Propositivo', value: 'propositivo' },
					{ name: 'Informativo', value: 'informativo' },
					{ name: 'Emotivo', value: 'emotivo' },
				],
				default: 'propositivo',
				displayOptions: {
					show: {
						operation: ['generate'],
					},
				},
				description: 'Tone of voice for the generated content',
			},

			// ------------------------------------------
			// Fields: List
			// ------------------------------------------
			{
				displayName: 'Status Filter',
				name: 'statusFilter',
				type: 'options',
				options: [
					{ name: 'All', value: '' },
					{ name: 'Draft', value: 'borrador' },
					{ name: 'Approved', value: 'aprobado' },
					{ name: 'Published', value: 'publicado' },
					{ name: 'Rejected', value: 'rechazado' },
				],
				default: '',
				displayOptions: {
					show: {
						operation: ['list'],
					},
				},
				description: 'Filter by content status',
			},
			{
				displayName: 'Limit',
				name: 'limit',
				type: 'number',
				default: 50,
				displayOptions: {
					show: {
						operation: ['list'],
					},
				},
				typeOptions: {
					minValue: 1,
					maxValue: 500,
				},
				description: 'Max number of results to return',
			},

			// ------------------------------------------
			// Fields: Update Status
			// ------------------------------------------
			{
				displayName: 'Content ID',
				name: 'contentId',
				type: 'string',
				default: '',
				required: true,
				displayOptions: {
					show: {
						operation: ['update_status'],
					},
				},
				description: 'Internal CRECE ID of the content piece',
			},
			{
				displayName: 'New Status',
				name: 'newStatus',
				type: 'options',
				options: [
					{ name: 'Draft', value: 'borrador' },
					{ name: 'Approved', value: 'aprobado' },
					{ name: 'Published', value: 'publicado' },
					{ name: 'Rejected', value: 'rechazado' },
				],
				default: 'aprobado',
				required: true,
				displayOptions: {
					show: {
						operation: ['update_status'],
					},
				},
				description: 'New status for the content piece',
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const returnData: INodeExecutionData[] = [];

		const operation = this.getNodeParameter('operation', 0) as string;

		for (let i = 0; i < items.length; i++) {
			try {
				if (operation === 'generate') {
					const dirigenteId = this.getNodeParameter('dirigenteId', i) as string;
					const formato = this.getNodeParameter('formato', i) as string;
					const tema = this.getNodeParameter('tema', i) as string;
					const tono = this.getNodeParameter('tono', i) as string;

					const response = await creceApiRequest.call(
						this,
						'POST',
						'/contenido/generate',
						{
							dirigente_id: dirigenteId,
							formato,
							tema,
							tono,
						},
					) as Record<string, unknown>;

					returnData.push({
						json: {
							operation: 'generate',
							dirigente_id: dirigenteId,
							formato,
							tema,
							tono,
							id: response.id,
							contenido: response.contenido ?? response.content,
							modelo_ia: response.modelo_ia,
							status: response.status ?? 'borrador',
							created_at: response.created_at,
						},
					});
				} else if (operation === 'list') {
					const dirigenteId = this.getNodeParameter('dirigenteId', i) as string;
					const statusFilter = this.getNodeParameter('statusFilter', i) as string;
					const limit = this.getNodeParameter('limit', i) as number;

					const query: Record<string, string | number | boolean> = {
						dirigente_id: dirigenteId,
						limit,
					};
					if (statusFilter) {
						query.status = statusFilter;
					}

					const response = await creceApiRequest.call(
						this,
						'GET',
						'/contenido/',
						undefined,
						query,
					);

					const items_list = Array.isArray(response) ? response : [response];
					for (const item of items_list) {
						returnData.push({
							json: item as Record<string, unknown>,
						});
					}
				} else if (operation === 'update_status') {
					const contentId = this.getNodeParameter('contentId', i) as string;
					const newStatus = this.getNodeParameter('newStatus', i) as string;

					const response = await creceApiRequest.call(
						this,
						'PATCH',
						`/contenido/${contentId}/estado`,
						{ status: newStatus },
					) as Record<string, unknown>;

					returnData.push({
						json: {
							operation: 'update_status',
							content_id: contentId,
							new_status: newStatus,
							success: true,
							...response,
						},
					});
				}
			} catch (error) {
				if (this.continueOnFail()) {
					returnData.push({
						json: {
							success: false,
							error: (error as Error).message,
						},
					});
					continue;
				}
				throw new NodeOperationError(
					this.getNode(),
					`Error in contenido/${operation}: ${(error as Error).message}`,
					{ itemIndex: i },
				);
			}
		}

		return [returnData];
	}
}
