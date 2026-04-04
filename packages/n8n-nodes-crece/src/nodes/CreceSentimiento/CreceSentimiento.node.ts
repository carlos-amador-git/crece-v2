import {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
	NodeOperationError,
} from 'n8n-workflow';

import { creceApiRequest } from '../shared/CreceApiRequest';

/**
 * CRECE Sentimiento -- Sentiment analysis node for political text.
 *
 * Leverages the CRECE NLP service (pysentimiento + spaCy) to analyze
 * sentiment of arbitrary text or retrieve pre-computed sentiment for
 * social media posts already tracked by the platform.
 *
 * Operations:
 * - analyze:            send raw text for real-time sentiment analysis
 * - get_post_sentiment: retrieve sentiment data for an existing social post
 */
export class CreceSentimiento implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'CRECE Sentimiento',
		name: 'creceSentimiento',
		icon: 'file:crece.svg',
		group: ['transform'],
		version: 1,
		subtitle: '={{$parameter["operation"]}}',
		description:
			'Analyze sentiment of political text or retrieve post sentiment using CRECE NLP',
		defaults: {
			name: 'CRECE Sentimiento',
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
						name: 'Analyze Text',
						value: 'analyze',
						description: 'Analyze sentiment of raw text using pysentimiento + spaCy',
						action: 'Analyze text sentiment',
					},
					{
						name: 'Get Post Sentiment',
						value: 'get_post_sentiment',
						description: 'Retrieve pre-computed sentiment for a tracked social post',
						action: 'Get post sentiment',
					},
				],
				default: 'analyze',
			},

			// ------------------------------------------
			// Fields: Analyze
			// ------------------------------------------
			{
				displayName: 'Text',
				name: 'text',
				type: 'string',
				default: '',
				required: true,
				displayOptions: {
					show: {
						operation: ['analyze'],
					},
				},
				typeOptions: {
					rows: 4,
				},
				description: 'Text to analyze for sentiment. Supports Spanish political discourse.',
			},
			{
				displayName: 'Platform',
				name: 'platform',
				type: 'options',
				options: [
					{ name: 'General', value: '' },
					{ name: 'Twitter / X', value: 'twitter' },
					{ name: 'Instagram', value: 'instagram' },
					{ name: 'Facebook', value: 'facebook' },
					{ name: 'TikTok', value: 'tiktok' },
					{ name: 'YouTube', value: 'youtube' },
				],
				default: '',
				displayOptions: {
					show: {
						operation: ['analyze'],
					},
				},
				description:
					'Source platform for normalization (Twitter skews negative, Instagram positive)',
			},

			// ------------------------------------------
			// Fields: Get Post Sentiment
			// ------------------------------------------
			{
				displayName: 'Post ID',
				name: 'postId',
				type: 'string',
				default: '',
				required: true,
				displayOptions: {
					show: {
						operation: ['get_post_sentiment'],
					},
				},
				description: 'Internal CRECE ID of the social media post',
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const returnData: INodeExecutionData[] = [];

		const operation = this.getNodeParameter('operation', 0) as string;

		for (let i = 0; i < items.length; i++) {
			try {
				if (operation === 'analyze') {
					const text = this.getNodeParameter('text', i) as string;
					const platform = this.getNodeParameter('platform', i) as string;

					if (!text.trim()) {
						throw new NodeOperationError(
							this.getNode(),
							'Text parameter cannot be empty',
							{ itemIndex: i },
						);
					}

					const body: Record<string, unknown> = { text };
					if (platform) {
						body.platform = platform;
					}

					const response = await creceApiRequest.call(
						this,
						'POST',
						'/social/analyze',
						body,
					) as Record<string, unknown>;

					returnData.push({
						json: {
							operation: 'analyze',
							text,
							platform: platform || 'general',
							sentiment: response.sentiment ?? response.label,
							score: response.score,
							positive: response.positive,
							negative: response.negative,
							neutral: response.neutral,
							topics: response.topics ?? [],
							controversy_score: response.controversy_score ?? null,
							entities: response.entities ?? [],
						},
					});
				} else if (operation === 'get_post_sentiment') {
					const postId = this.getNodeParameter('postId', i) as string;

					const response = await creceApiRequest.call(
						this,
						'GET',
						`/social/posts/${postId}/sentiment`,
					) as Record<string, unknown>;

					returnData.push({
						json: {
							operation: 'get_post_sentiment',
							post_id: postId,
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
					`Error in sentimiento/${operation}: ${(error as Error).message}`,
					{ itemIndex: i },
				);
			}
		}

		return [returnData];
	}
}
