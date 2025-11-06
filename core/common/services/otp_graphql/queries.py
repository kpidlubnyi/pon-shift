from enum import StrEnum


class OTPGraphQLQueries(StrEnum):
    GET_TRIPS = """
        query trip($accessEgressPenalty: [PenaltyForStreetMode!], $alightSlackDefault: Int, $alightSlackList: [TransportModeSlack], $arriveBy: Boolean, $banned: InputBanned, $bicycleOptimisationMethod: BicycleOptimisationMethod, $bikeSpeed: Float, $boardSlackDefault: Int, $boardSlackList: [TransportModeSlack], $bookingTime: DateTime, $dateTime: DateTime, $filters: [TripFilterInput!], $fromLocation: Location!, $ignoreRealtimeUpdates: Boolean, $includePlannedCancellations: Boolean, $includeRealtimeCancellations: Boolean, $itineraryFilters: ItineraryFilters, $locale: Locale, $maxAccessEgressDurationForMode: [StreetModeDurationInput!], $maxDirectDurationForMode: [StreetModeDurationInput!], $maximumAdditionalTransfers: Int, $maximumTransfers: Int, $modes: Modes, $numTripPatterns: Int, $pageCursor: String, $relaxTransitGroupPriority: RelaxCostInput, $searchWindow: Int, $timetableView: Boolean, $toLocation: Location!, $transferPenalty: Int, $transferSlack: Int, $triangleFactors: TriangleFactors, $useBikeRentalAvailabilityInformation: Boolean, $via: [TripViaLocationInput!], $waitReluctance: Float, $walkReluctance: Float, $walkSpeed: Float, $wheelchairAccessible: Boolean, $whiteListed: InputWhiteListed) {
            trip(
                accessEgressPenalty: $accessEgressPenalty
                alightSlackDefault: $alightSlackDefault
                alightSlackList: $alightSlackList
                arriveBy: $arriveBy
                banned: $banned
                bicycleOptimisationMethod: $bicycleOptimisationMethod
                bikeSpeed: $bikeSpeed
                boardSlackDefault: $boardSlackDefault
                boardSlackList: $boardSlackList
                bookingTime: $bookingTime
                dateTime: $dateTime
                filters: $filters
                from: $fromLocation
                ignoreRealtimeUpdates: $ignoreRealtimeUpdates
                includePlannedCancellations: $includePlannedCancellations
                includeRealtimeCancellations: $includeRealtimeCancellations
                itineraryFilters: $itineraryFilters
                locale: $locale
                maxAccessEgressDurationForMode: $maxAccessEgressDurationForMode
                maxDirectDurationForMode: $maxDirectDurationForMode
                maximumAdditionalTransfers: $maximumAdditionalTransfers
                maximumTransfers: $maximumTransfers
                modes: $modes
                numTripPatterns: $numTripPatterns
                pageCursor: $pageCursor
                relaxTransitGroupPriority: $relaxTransitGroupPriority
                searchWindow: $searchWindow
                timetableView: $timetableView
                to: $toLocation
                transferPenalty: $transferPenalty
                transferSlack: $transferSlack
                triangleFactors: $triangleFactors
                useBikeRentalAvailabilityInformation: $useBikeRentalAvailabilityInformation
                via: $via
                waitReluctance: $waitReluctance
                walkReluctance: $walkReluctance
                walkSpeed: $walkSpeed
                wheelchairAccessible: $wheelchairAccessible
                whiteListed: $whiteListed
            ) {
                previousPageCursor
                nextPageCursor
                tripPatterns {
                    aimedStartTime
                    expectedStartTime
                    aimedEndTime
                    expectedEndTime 
                    duration
                    distance
                    legs {
                        serviceJourney {
                            id    
                        }
                        mode
                        aimedStartTime
                        expectedStartTime
                        aimedEndTime
                        expectedEndTime
                        realtime
                        distance
                        duration
                        fromPlace {
                            quay {
                                ... quayDetails
                            }
                        }
                        toPlace {
                            quay {
                                ... quayDetails
                            }
                        }
                        authority {
                            id
                            name
                        }
                        pointsOnLink {
                           points
                        }
                        interchangeTo {
                          staySeated
                        }
                        interchangeFrom {
                           staySeated
                        }
                    }
                    systemNotices {
                        tag
                    }
                }
            }
        }

        fragment quayDetails on Quay {
            id
            name
            latitude
            longitude
            wheelchairAccessible
        }
"""