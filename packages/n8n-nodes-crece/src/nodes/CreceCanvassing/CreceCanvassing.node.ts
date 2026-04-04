import {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
	NodeOperationError,
} from 'n8n-workflow';

import { creceApiRequest } from '../shared/CreceApiRequest';

/**
 * CRECE Canvassing -- Smart canvassing route management node.
 *
 * Connects to the CRECE Smart Canvassing module to generate optimized
 * door-to-door routes, list existing routes, and mark visited points.
 *
 * Operations:
 * - optimize:     generate an optimized canvassing route for a given section
 * - list_routes:  list existing canvassing routes
 * - mark_visited: mark a specific point on a route as visited
 */
export class CreceCanvassing implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'CRECE Canvassing',
		name: 'creceCanvassing',
		icon: 'file:crece.svg',
		group: ['transform'],
		version: 1,
		subtitle: '={{$parameter["operation"]}}',
		description:
			'Generate optimized canvassing routes, list routes, and track visited points',
		defaults: {
			name: 'CRECE Canvassing',
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
						name: 'Optimize Route',
						value: 'optimize',
						description: 'Generate an optimized door-to-door canvassing route',
						action: 'Optimize canvassing route',
					},
					{
						name: 'List Routes',
						value: 'list_routes',
						description: 'List existing canvassing routes',
						action: 'List canvassing routes',
					},
					{
						name: 'Mark Visited',
						value: 'mark_visited',
						description: 'Mark a specific point on a route as visited',
						action: 'Mark point as visited',
					},
				],
				default: 'optimize',
			},

			// ------------------------------------------
			// Fields: Optimize
			// ------------------------------------------
			{
				displayName: 'Seccion Electoral ID',
				name: 'seccionId',
				type: 'number',
				default: 0,
				required: true,
				displayOptions: {
					show: {
						operation: ['optimize'],
					},
				},
				description: 'Electoral section number for the canvassing route',
			},
			{
				displayName: 'Encuestador ID',
				name: 'encuestadorId',
				type: 'string',
				default: '',
				required: true,
				displayOptions: {
					show: {
						operation: ['optimize'],
					},
				},
				description: 'Internal ID of the field worker (encuestador)',
			},
			{
				displayName: 'Fecha',
				name: 'fecha',
				type: 'dateTime',
				default: '',
				required: true,
				displayOptions: {
					show: {
						operation: ['optimize'],
					},
				},
				description: 'Scheduled date for the canvassing route (ISO 8601)',
			},
			{
				displayName: 'Max Puntos',
				name: 'maxPuntos',
				type: 'number',
				default: 30,
				displayOptions: {
					show: {
						operation: ['optimize'],
					},
				},
				typeOptions: {
					minValue: 5,
					maxValue: 200,
				},
				description: 'Maximum number of points (households) in the route',
			},

			// ------------------------------------------
			// Fields: List Routes
			// ------------------------------------------
			{
				displayName: 'Seccion Filter',
				name: 'seccionFilter',
				type: 'number',
				default: 0,
				displayOptions: {
					show: {
						operation: ['list_routes'],
					},
				},
				description: 'Filter routes by electoral section. Leave 0 for all.',
			},
			{
				displayName: 'Encuestador Filter',
				name: 'encuestadorFilter',
				type: 'string',
				default: '',
				displayOptions: {
					show: {
						operation: ['list_routes'],
					},
				},
				description: 'Filter routes by encuestador ID. Leave empty for all.',
			},
			{
				displayName: 'Limit',
				name: 'limit',
				type: 'number',
				default: 50,
				displayOptions: {
					show: {
						operation: ['list_routes'],
					},
				},
				typeOptions: {
					minValue: 1,
					maxValue: 500,
				},
				description: 'Max number of routes to return',
			},

			// ------------------------------------------
			// Fields: Mark Visited
			// ------------------------------------------
			{
				displayName: 'Route ID',
				name: 'routeId',
				type: 'string',
				default: '',
				required: true,
				displayOptions: {
					show: {
						operation: ['mark_visited'],
					},
				},
				description: 'Internal CRECE ID of the canvassing route',
			},
			{
				displayName: 'Punto ID',
				name: 'puntoId',
				type: 'string',
				default: '',
				required: true,
				displayOptions: {
					show: {
						operation: ['mark_visited'],
					},
				},
				description: 'Internal CRECE ID of the point within the route',
			},
			{
				displayName: 'Notes',
				name: 'notes',
				type: 'string',
				default: '',
				displayOptions: {
					show: {
						operation: ['mark_visited'],
					},
				},
				typeOptions: {
					rows: 3,
				},
				description: 'Optional field notes from the visit',
			},
			{
				displayName: 'Resultado',
				name: 'resultado',
				type: 'options',
				options: [
					{ name: 'Contacto exitoso', value: 'contacto_exitoso' },
					{ name: 'No encontrado', value: 'no_encontrado' },
					{ name: 'Rechazado', value: 'rechazado' },
					{ name: 'Ausente', value: 'ausente' },
				],
				default: 'contacto_exitoso',
				displayOptions: {
					show: {
						operation: ['mark_visited'],
					},
				},
				description: 'Result of the visit attempt',
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const returnData: INodeExecutionData[] = [];

		const operation = this.getNodeParameter('operation', 0) as string;

		for (let i = 0; i < items.length; i++) {
			try {
				if (operation === 'optimize') {
					const seccionId = this.getNodeParameter('seccionId', i) as number;
					const encuestadorId = this.getNodeParameter('encuestadorId', i) as string;
					const fecha = this.getNodeParameter('fecha', i) as string;
					const maxPuntos = this.getNodeParameter('maxPuntos', i) as number;

					const response = await creceApiRequest.call(
						this,
						'POST',
						'/canvassing/optimize',
						{
							seccion_id: seccionId,
							encuestador_id: encuestadorId,
							fecha,
							max_puntos: maxPuntos,
						},
					) as Record<string, unknown>;

					returnData.push({
						json: {
							operation: 'optimize',
							id: response.id,
							seccion_id: seccionId,
							encuestador_id: encuestadorId,
							fecha,
							total_puntos: response.total_puntos ?? (response.puntos as unknown[] | undefined)?.length ?? 0,
							distancia_total_km: response.distancia_total_km,
							tiempo_estimado_min: response.tiempo_estimado_min,
							puntos: response.puntos,
						},
					});
				} else if (operation === 'list_routes') {
					const seccionFilter = this.getNodeParameter('seccionFilter', i) as number;
					const encuestadorFilter = this.getNodeParameter('encuestadorFilter', i) as string;
					const limit = this.getNodeParameter('limit', i) as number;

					const query: Record<string, string | number | boolean> = { limit };
					if (seccionFilter > 0) query.seccion_id = seccionFilter;
					if (encuestadorFilter) query.encuestador_id = encuestadorFilter;

					const response = await creceApiRequest.call(
						this,
						'GET',
						'/canvassing/routes',
						undefined,
						query,
					);

					const routes = Array.isArray(response) ? response : [response];
					for (const route of routes) {
						returnData.push({
							json: route as Record<string, unknown>,
						});
					}
				} else if (operation === 'mark_visited') {
					const routeId = this.getNodeParameter('routeId', i) as string;
					const puntoId = this.getNodeParameter('puntoId', i) as string;
					const notes = this.getNodeParameter('notes', i) as string;
					const resultado = this.getNodeParameter('resultado', i) as string;

					const body: Record<string, unknown> = {
						visited: true,
						resultado,
					};
					if (notes) {
						body.notes = notes;
					}

					const response = await creceApiRequest.call(
						this,
						'PATCH',
						`/canvassing/routes/${routeId}/punto/${puntoId}`,
						body,
					) as Record<string, unknown>;

					returnData.push({
						json: {
							operation: 'mark_visited',
							route_id: routeId,
							punto_id: puntoId,
							resultado,
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
					`Error in canvassing/${operation}: ${(error as Error).message}`,
					{ itemIndex: i },
				);
			}
		}

		return [returnData];
	}
}
