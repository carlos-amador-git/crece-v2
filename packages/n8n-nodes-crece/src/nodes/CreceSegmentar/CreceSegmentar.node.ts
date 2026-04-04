import {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
	NodeOperationError,
} from 'n8n-workflow';

import { creceApiRequest } from '../shared/CreceApiRequest';

/**
 * CRECE Segmentar — Citizen segmentation node for political campaigns.
 *
 * Connects to the CRECE API /ciudadanos/ endpoint to filter and count
 * citizens by electoral section, voting intention, demographics, and
 * voter scoring criteria.
 *
 * Operations:
 * - segment: retrieve a filtered list of ciudadanos
 * - count:   return the total count matching the filters
 */
export class CreceSegmentar implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'CRECE Segmentar',
		name: 'creceSegmentar',
		icon: 'file:crece.svg',
		group: ['transform'],
		version: 1,
		subtitle: '={{$parameter["operation"]}}',
		description:
			'Segment citizens by electoral section, voting intention, demographics, and voter score',
		defaults: {
			name: 'CRECE Segmentar',
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
						name: 'Segment',
						value: 'segment',
						description: 'Filter and retrieve a list of citizens matching criteria',
						action: 'Segment citizens by criteria',
					},
					{
						name: 'Count',
						value: 'count',
						description: 'Count citizens matching the given criteria',
						action: 'Count matching citizens',
					},
				],
				default: 'segment',
			},

			// ------------------------------------------
			// Filter parameters
			// ------------------------------------------
			{
				displayName: 'Seccion Electoral ID',
				name: 'seccionId',
				type: 'number',
				default: 0,
				description: 'Filter by electoral section number (seccion INE). Leave 0 for all.',
			},
			{
				displayName: 'Intencion de Voto',
				name: 'intencionVoto',
				type: 'options',
				options: [
					{ name: 'All', value: '' },
					{ name: 'MC (Movimiento Ciudadano)', value: 'MC' },
					{ name: 'MORENA', value: 'MORENA' },
					{ name: 'PAN', value: 'PAN' },
					{ name: 'PRI', value: 'PRI' },
					{ name: 'PRD', value: 'PRD' },
					{ name: 'PVEM', value: 'PVEM' },
					{ name: 'PT', value: 'PT' },
					{ name: 'Indeciso', value: 'INDECISO' },
					{ name: 'Abstencion', value: 'ABSTENCION' },
				],
				default: '',
				description: 'Filter by declared voting intention',
			},
			{
				displayName: 'Rango de Edad',
				name: 'edadRango',
				type: 'options',
				options: [
					{ name: 'All', value: '' },
					{ name: '18-25', value: '18-25' },
					{ name: '26-35', value: '26-35' },
					{ name: '36-45', value: '36-45' },
					{ name: '46-55', value: '46-55' },
					{ name: '56-65', value: '56-65' },
					{ name: '65+', value: '65+' },
				],
				default: '',
				description: 'Filter by age range',
			},
			{
				displayName: 'Escolaridad',
				name: 'escolaridad',
				type: 'options',
				options: [
					{ name: 'All', value: '' },
					{ name: 'Primaria', value: 'primaria' },
					{ name: 'Secundaria', value: 'secundaria' },
					{ name: 'Preparatoria', value: 'preparatoria' },
					{ name: 'Universidad', value: 'universidad' },
					{ name: 'Posgrado', value: 'posgrado' },
				],
				default: '',
				description: 'Filter by education level',
			},
			{
				displayName: 'Solo Simpatizantes',
				name: 'esSimpatizante',
				type: 'boolean',
				default: false,
				description: 'Whether to only return confirmed MC supporters',
			},
			{
				displayName: 'Score Minimo',
				name: 'scoreMin',
				type: 'number',
				default: 0,
				description: 'Minimum voter score (0-100). Leave 0 for no minimum.',
				typeOptions: {
					minValue: 0,
					maxValue: 100,
				},
			},
			{
				displayName: 'Score Maximo',
				name: 'scoreMax',
				type: 'number',
				default: 100,
				description: 'Maximum voter score (0-100). Leave 100 for no maximum.',
				typeOptions: {
					minValue: 0,
					maxValue: 100,
				},
			},
			{
				displayName: 'Limit',
				name: 'limit',
				type: 'number',
				default: 100,
				description: 'Max number of results to return',
				displayOptions: {
					show: {
						operation: ['segment'],
					},
				},
				typeOptions: {
					minValue: 1,
					maxValue: 10000,
				},
			},
			{
				displayName: 'Offset',
				name: 'offset',
				type: 'number',
				default: 0,
				description: 'Number of results to skip (for pagination)',
				displayOptions: {
					show: {
						operation: ['segment'],
					},
				},
				typeOptions: {
					minValue: 0,
				},
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const returnData: INodeExecutionData[] = [];

		const operation = this.getNodeParameter('operation', 0) as string;

		for (let i = 0; i < items.length; i++) {
			try {
				const query: Record<string, string | number | boolean> = {};

				const seccionId = this.getNodeParameter('seccionId', i) as number;
				if (seccionId > 0) query.seccion_id = seccionId;

				const intencionVoto = this.getNodeParameter('intencionVoto', i) as string;
				if (intencionVoto) query.intencion_voto = intencionVoto;

				const edadRango = this.getNodeParameter('edadRango', i) as string;
				if (edadRango) query.edad_rango = edadRango;

				const escolaridad = this.getNodeParameter('escolaridad', i) as string;
				if (escolaridad) query.escolaridad = escolaridad;

				const esSimpatizante = this.getNodeParameter('esSimpatizante', i) as boolean;
				if (esSimpatizante) query.es_simpatizante = true;

				const scoreMin = this.getNodeParameter('scoreMin', i) as number;
				if (scoreMin > 0) query.score_min = scoreMin;

				const scoreMax = this.getNodeParameter('scoreMax', i) as number;
				if (scoreMax < 100) query.score_max = scoreMax;

				if (operation === 'segment') {
					const limit = this.getNodeParameter('limit', i) as number;
					const offset = this.getNodeParameter('offset', i) as number;
					query.limit = limit;
					query.skip = offset;

					const response = await creceApiRequest.call(
						this,
						'GET',
						'/ciudadanos/',
						undefined,
						query,
					);

					const ciudadanos = Array.isArray(response) ? response : [response];
					for (const ciudadano of ciudadanos) {
						returnData.push({
							json: ciudadano as Record<string, unknown>,
						});
					}
				} else if (operation === 'count') {
					query.count_only = true;

					const response = await creceApiRequest.call(
						this,
						'GET',
						'/ciudadanos/',
						undefined,
						query,
					) as Record<string, unknown>;

					returnData.push({
						json: {
							operation: 'count',
							total: response.total ?? response.count ?? 0,
							filters: query,
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
					`Error in segmentar/${operation}: ${(error as Error).message}`,
					{ itemIndex: i },
				);
			}
		}

		return [returnData];
	}
}
