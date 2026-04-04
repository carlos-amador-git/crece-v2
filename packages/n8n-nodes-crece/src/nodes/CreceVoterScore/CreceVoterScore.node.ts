import {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
	NodeOperationError,
} from 'n8n-workflow';

import { creceApiRequest } from '../shared/CreceApiRequest';

/**
 * CRECE VoterScore -- Voter scoring operations node.
 *
 * Manages the CRECE voter scoring system that assigns a 0-100 propensity
 * score to each citizen based on demographics, engagement history,
 * social media interaction, and canvassing results.
 *
 * Operations:
 * - score_all:     trigger a full scoring run across all citizens
 * - get_score:     retrieve the score for a specific citizen
 * - get_segments:  retrieve the segment distribution (high/medium/low propensity)
 */
export class CreceVoterScore implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'CRECE Voter Score',
		name: 'creceVoterScore',
		icon: 'file:crece.svg',
		group: ['transform'],
		version: 1,
		subtitle: '={{$parameter["operation"]}}',
		description:
			'Run voter scoring, retrieve individual scores, and view segment distributions',
		defaults: {
			name: 'CRECE Voter Score',
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
						name: 'Score All',
						value: 'score_all',
						description: 'Trigger a full voter scoring run for all citizens',
						action: 'Run voter scoring for all citizens',
					},
					{
						name: 'Get Score',
						value: 'get_score',
						description: 'Retrieve the voter score for a specific citizen',
						action: 'Get voter score',
					},
					{
						name: 'Get Segments',
						value: 'get_segments',
						description: 'Retrieve the segment distribution across all scored citizens',
						action: 'Get segment distribution',
					},
				],
				default: 'get_score',
			},

			// ------------------------------------------
			// Fields: Score All
			// ------------------------------------------
			{
				displayName: 'Seccion Filter',
				name: 'seccionFilter',
				type: 'number',
				default: 0,
				displayOptions: {
					show: {
						operation: ['score_all'],
					},
				},
				description:
					'Limit scoring run to a specific electoral section. Leave 0 to score all.',
			},
			{
				displayName: 'Force Recalculation',
				name: 'forceRecalc',
				type: 'boolean',
				default: false,
				displayOptions: {
					show: {
						operation: ['score_all'],
					},
				},
				description:
					'Whether to force recalculation even if scores are fresh (less than 24h old)',
			},

			// ------------------------------------------
			// Fields: Get Score
			// ------------------------------------------
			{
				displayName: 'Citizen ID',
				name: 'citizenId',
				type: 'string',
				default: '',
				required: true,
				displayOptions: {
					show: {
						operation: ['get_score'],
					},
				},
				description: 'Internal CRECE ID of the citizen (ciudadano)',
			},

			// ------------------------------------------
			// Fields: Get Segments
			// ------------------------------------------
			{
				displayName: 'Seccion Filter',
				name: 'segmentSeccionFilter',
				type: 'number',
				default: 0,
				displayOptions: {
					show: {
						operation: ['get_segments'],
					},
				},
				description:
					'Filter segment distribution by electoral section. Leave 0 for global.',
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const returnData: INodeExecutionData[] = [];

		const operation = this.getNodeParameter('operation', 0) as string;

		for (let i = 0; i < items.length; i++) {
			try {
				if (operation === 'score_all') {
					const seccionFilter = this.getNodeParameter('seccionFilter', i) as number;
					const forceRecalc = this.getNodeParameter('forceRecalc', i) as boolean;

					const body: Record<string, unknown> = {
						force: forceRecalc,
					};
					if (seccionFilter > 0) {
						body.seccion_id = seccionFilter;
					}

					const response = await creceApiRequest.call(
						this,
						'POST',
						'/voter-scoring/run',
						body,
					) as Record<string, unknown>;

					returnData.push({
						json: {
							operation: 'score_all',
							task_id: response.task_id ?? response.id,
							status: response.status ?? 'queued',
							total_scored: response.total_scored ?? null,
							seccion_filter: seccionFilter > 0 ? seccionFilter : 'all',
							forced: forceRecalc,
							started_at: response.started_at ?? response.created_at,
						},
					});
				} else if (operation === 'get_score') {
					const citizenId = this.getNodeParameter('citizenId', i) as string;

					const response = await creceApiRequest.call(
						this,
						'GET',
						`/voter-scoring/${citizenId}`,
					) as Record<string, unknown>;

					returnData.push({
						json: {
							operation: 'get_score',
							citizen_id: citizenId,
							score: response.score,
							segment: response.segment,
							components: response.components ?? {
								demographics: response.demographics_score,
								engagement: response.engagement_score,
								social: response.social_score,
								canvassing: response.canvassing_score,
							},
							last_calculated: response.last_calculated ?? response.updated_at,
						},
					});
				} else if (operation === 'get_segments') {
					const segmentSeccionFilter = this.getNodeParameter(
						'segmentSeccionFilter',
						i,
					) as number;

					const query: Record<string, string | number | boolean> = {};
					if (segmentSeccionFilter > 0) {
						query.seccion_id = segmentSeccionFilter;
					}

					const response = await creceApiRequest.call(
						this,
						'GET',
						'/voter-scoring/segments',
						undefined,
						query,
					) as Record<string, unknown>;

					returnData.push({
						json: {
							operation: 'get_segments',
							seccion_filter: segmentSeccionFilter > 0 ? segmentSeccionFilter : 'all',
							total_scored: response.total_scored ?? response.total,
							segments: response.segments ?? {
								high: response.high,
								medium: response.medium,
								low: response.low,
							},
							average_score: response.average_score,
							distribution: response.distribution ?? null,
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
					`Error in voter-score/${operation}: ${(error as Error).message}`,
					{ itemIndex: i },
				);
			}
		}

		return [returnData];
	}
}
