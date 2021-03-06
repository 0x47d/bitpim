### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
### Copyright (C) 2006 Roger Binns <rogerb@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

import helpids

# phone carriers
c_vzw='Verizon Wireless'
c_cingular='Cingular'
c_att='AT&T'
c_telus='Telus Mobility'
c_alltel='Alltel'
c_bell='Bell Mobility'
c_sprint='Sprint'
c_pelephone='Pelephone'
c_sti='STI Mobile'
c_other='Other'
if __debug__:
    c_tmobileusa='T-Mobile USA'

# phone brands
b_lg='LG'
b_samsung='Samsung'
b_sanyo='Sanyo'
b_sk='SK'
b_toshiba='Toshiba'
b_other='Other'
b_audiovox='Audiovox'
b_moto='Motorola'

_phonedata= { 'LG-AX8600': { 'module': 'com_lgax8600',
	    		     'carrier': [c_alltel],
			     'brand': b_lg,
			     'helpid': helpids.ID_PHONE_LGAX8600,
	    		     },
	      'LG-G4015': { 'module': 'com_lgg4015',
                            'carrier': [c_att],
                            'brand': b_lg,
                            'helpid': helpids.ID_PHONE_LGG4015,
                            },
              'LG-C2000': { 'module': 'com_lgc2000',
                            'carrier': [c_cingular],
                            'brand': b_lg,
                            'helpid': helpids.ID_PHONE_LGC2000,
                            },
              'LG-LX570 (Muziq)': { 'module': 'com_lglx570',
                                    'carrier': [c_sprint],
                                    'brand': b_lg,
                                    'helpid': helpids.ID_PHONE_LGLX570,
                            },
              'LG-UX5000': { 'module': 'com_lgux5000',
                             'brand': b_lg,
                             'carrier': [c_vzw],
                             'helpid': helpids.ID_PHONE_LGUX5000,
                             },
              'LG-VX3200': { 'module': 'com_lgvx3200',
                             'brand': b_lg,
                             'helpid': helpids.ID_PHONE_LGVX3200,
                             },
              'LG-VX4400': { 'module': 'com_lgvx4400',
                             'brand': b_lg,
                             'carrier': [c_vzw],
                             'helpid': helpids.ID_PHONE_LGVX4400,
                             },
              'LG-VX4500': { 'module': 'com_lgvx4500',
                             'brand': b_lg,
                             'helpid': helpids.ID_PHONE_LGVX4500,
                             },
              'LG-VX4600': { 'module': 'com_lgvx4600',
                             'carrier': [c_telus],
                             'brand': b_lg,
                             'helpid': None,
                             },
              'LG-VX4650': { 'module': 'com_lgvx4650',
                             'carrier': [c_vzw],
                             'brand': b_lg,
                             'helpid': helpids.ID_PHONE_LGVX4650,
                             },
              'LG-VX5200': { 'module': 'com_lgvx5200',
                             'carrier': [c_vzw],
                             'brand': b_lg,
                             'helpid': helpids.ID_PHONE_LGVX5200,
                             },
              'LG-VX5300': { 'module': 'com_lgvx5300',
                             'carrier': [c_vzw],
                             'brand': b_lg,
                             'helpid': helpids.ID_PHONE_LGVX5300,
                             },
              'LG-VX5400': { 'module': 'com_lgvx5400',
                             'carrier': [c_vzw],
                             'brand': b_lg,
                             'helpid': None,
                             },
              'LG-LX5450': { 'module': 'com_lglx5450',
                             'carrier': [c_alltel],
                             'brand': b_lg,
                             'helpid': None,
                             },
              'LG-VX5500': { 'module': 'com_lgvx5500',
                             'carrier': [c_vzw],
                             'brand': b_lg,
                             'helpid': None,
                             },
              'LG-LX5550': { 'module': 'com_lglx5550',
                             'carrier': [c_alltel],
                             'brand': b_lg,
                             'helpid': None,
                             },
              'LG-VX6000': { 'module': 'com_lgvx6000',
                             'brand': b_lg,
                             'helpid': helpids.ID_PHONE_LGVX6000,
                             },
              'LG-VX6100': { 'module': 'com_lgvx6100',
                             'brand': b_lg,
                             'helpid': helpids.ID_PHONE_LGVX6100,
                             },
              'LG-LG6190': { 'module': 'com_lglg6190',
                             'carrier': [c_bell],
                             'brand': b_lg,
                             'helpid': None,
                             },
              'LG-LG6200': { 'module': 'com_lglg6200',
                             'carrier': [c_bell],
                             'brand': b_lg,
                             'helpid': None,
                             },
              'LG-VX7000': { 'module': 'com_lgvx7000',
                             'brand': b_lg,
                             'helpid': helpids.ID_PHONE_LGVX7000,
                             },
              'LG-VX8000': { 'module': 'com_lgvx8000',
                             'carrier': [c_vzw],
                             'brand': b_lg,
                             'helpid': helpids.ID_PHONE_LGVX8000,
                             },
              'LG-LG8100': { 'module': 'com_lglg8100',
                             'carrier': [c_telus],
                             'brand': b_lg,
                             'helpid': None,
                             },
              'LG-VX8100': { 'module': 'com_lgvx8100',
                             'carrier': [c_vzw],
                             'brand': b_lg,
                             'helpid': helpids.ID_PHONE_LGVX8100,
                             },
              'LG-VX8300': { 'module': 'com_lgvx8300',
                             'carrier': [c_vzw],
                             'brand': b_lg,
                             'helpid': helpids.ID_PHONE_LGVX8300,
                             },
              'LG-VX8350': { 'module': 'com_lgvx8350',
                             'carrier': [c_vzw],
                             'brand': b_lg,
                             'helpid': None,
                             },
              'LG-VX8500 (Chocolate)': { 'module': 'com_lgvx8500',
                                         'carrier': [c_vzw],
                                         'brand': b_lg,
                                         'helpid': helpids.ID_PHONE_LGVX8500,
                                         },
              'LG-VX8550 (Chocolate 2)': { 'module': 'com_lgvx8550',
                                           'carrier': [c_vzw],
                                           'brand': b_lg,
                                           'helpid': None,
                                           },
              'LG-VX8560 (Chocolate 3)': { 'module': 'com_lgvx8560',
                                           'carrier': [c_vzw],
                                           'brand': b_lg,
                                           'helpid': helpids.ID_PHONE_LGVX8560,
                                           },
              'LG-VX8575 (Chocolate Touch)': { 'module': 'com_lgvx8575',
                                           'carrier': [c_vzw],
                                           'brand': b_lg,
                                           'helpid': helpids.ID_PHONE_LGVX8575,
                                           },
              'LG-VX8600': { 'module': 'com_lgvx8600',
                             'carrier': [c_vzw],
                             'brand': b_lg,
                             'helpid': helpids.ID_PHONE_LGVX8600,
                             },
              'LG-VX8610 (Decoy)': { 'module': 'com_lgvx8610',
                                     'carrier': [c_vzw],
                                     'brand': b_lg,
                                     'helpid': helpids.ID_PHONE_LGVX8610,
                             },
              'LG-VX8700': { 'module': 'com_lgvx8700',
                             'carrier': [c_vzw],
                             'brand': b_lg,
                             'helpid': helpids.ID_PHONE_LGVX8700,
                             },
              'LG-VX8800 (Venus)': { 'module': 'com_lgvx8800',
                                     'carrier': [c_vzw],
                                     'brand': b_lg,
                                     'helpid': helpids.ID_PHONE_LGVX8800,
                                     },
              'LG-VX9400': { 'module': 'com_lgvx9400',
                             'carrier': [c_vzw],
                             'brand': b_lg,
                             'helpid': None,
                             },
              'LG-VX9600 (Versa)': { 'module': 'com_lgvx9600',
                                     'carrier': [c_vzw],
                                     'brand': b_lg,
                                     'helpid': helpids.ID_PHONE_LGVX9600,
                                    },
              'LG-VX9700 (Dare)': { 'module': 'com_lgvx9700',
                                    'carrier': [c_vzw],
                                    'brand': b_lg,
                                    'helpid': helpids.ID_PHONE_LGVX9700,
                                    },
              'LG-VX9800': { 'module': 'com_lgvx9800',
                             'carrier': [c_vzw],
                             'brand': b_lg,
                             'helpid': helpids.ID_PHONE_LGVX9800,
                             },
              'LG-VX9900 (enV)': { 'module': 'com_lgvx9900',
                                   'carrier': [c_vzw],
                                   'brand': b_lg,
                                   'helpid': helpids.ID_PHONE_LGVX9900,
                                   },
              'LG-VX9100 (enV 2)': { 'module': 'com_lgvx9100',
                                     'carrier': [c_vzw],
                                     'brand': b_lg,
                                     'helpid': helpids.ID_PHONE_LGVX9100,
                                     },
              'LG-VX9200 (enV 3)': { 'module': 'com_lgvx9200',
                                     'carrier': [c_vzw],
                                     'brand': b_lg,
                                     'helpid': helpids.ID_PHONE_LGVX9200,
                                     },
              'LG-CX9200 (Keybo 2)': { 'module': 'com_lgcx9200',
                                     'carrier': [c_telus],
                                     'brand': b_lg,
                                     'helpid': helpids.ID_PHONE_LGVX9200,
                                     },
              'LG-VX10000 (Voyager)': { 'module': 'com_lgvx10000',
                                        'carrier': [c_vzw],
                                        'brand': b_lg,
                                        'helpid': helpids.ID_PHONE_LGVX10000,
                                        },
              'LG-VX11000 (enV Touch)': { 'module': 'com_lgvx11000',
                                        'carrier': [c_vzw],
                                        'brand': b_lg,
                                        'helpid': helpids.ID_PHONE_LGVX11000,
                                        },
              'LG-VI125': { 'module': 'com_lgvi125',
                            'carrier': [c_sprint],
                            'brand': b_lg,
                            'helpid': None,
                            },
              'LG-PM225': { 'module': 'com_lgpm225',
                            'carrier': [c_sprint],
                            'brand': b_lg,
                            'helpid': helpids.ID_PHONE_LGPM225,
                            },
              'LG-PM325': { 'module': 'com_lgpm325',
                            'carrier': [c_sprint],
                            'brand': b_lg,
                            'helpid': None,
                            },
              'LG-TM520': { 'module': 'com_lgtm520',
                            'brand': b_lg,
                            'helpid': None,
                            },
              'LG-VX10': { 'module': 'com_lgtm520',
                           'brand': b_lg,
                           'helpid': None,
                           },
              'MM-5600': { 'module': 'com_sanyo5600',
                           'carrier': [c_sprint],
                           'brand': b_sanyo,
                           'helpid': helpids.ID_PHONE_SANYOOTHERS,
                           },
              'SCP-6600 (Katana)': { 'module': 'com_sanyo6600',
                                     'carrier': [c_sprint],
                                     'brand': b_sanyo,
                                     'helpid': helpids.ID_PHONE_SANYOSCP6600,
                                     },
              'SCP-6650 (Katana-II)': { 'module': 'com_sanyo6650',
                                     'carrier': [c_sprint],
                                     'brand': b_sanyo,
                                     'helpid': helpids.ID_PHONE_SANYOSCP6600,
                                     },
              'MM-7400': { 'module': 'com_sanyo7400',
                           'carrier': [c_sprint],
                           'brand': b_sanyo,
                           'helpid': helpids.ID_PHONE_SANYOOTHERS,
                           },
              'MM-7500': { 'module': 'com_sanyo7500',
                           'carrier': [c_sprint],
                           'brand': b_sanyo,
                           'helpid': helpids.ID_PHONE_SANYOOTHERS,
                           },
              'MM-8300': { 'module': 'com_sanyo8300',
                           'carrier': [c_sprint],
                           'brand': b_sanyo,
                           'helpid': helpids.ID_PHONE_SANYOOTHERS,
                           },
              'SCP-8400': { 'module': 'com_sanyo8400',
                            'carrier': [c_sprint],
                            'brand': b_sanyo,
                            'helpid': helpids.ID_PHONE_SANYOOTHERS,
                            },
              'PM-8200': { 'module': 'com_sanyo8200',
                           'carrier': [c_sprint],
                           'brand': b_sanyo,
                           'helpid': helpids.ID_PHONE_SANYOOTHERS,
                           },
              'RL-4920': { 'module': 'com_sanyo4920',
                           'carrier': [c_sprint],
                           'brand': b_sanyo,
                           'helpid': helpids.ID_PHONE_SANYOOTHERS,
                           },
              'RL-4930': { 'module': 'com_sanyo4930',
                           'carrier': [c_sprint],
                           'brand': b_sanyo,
                           'helpid': helpids.ID_PHONE_SANYOOTHERS,
                           },
              'SCP-200': { 'module': 'com_sanyo200',
                            'carrier': [c_sprint],
                            'brand': b_sanyo,
                            'helpid': helpids.ID_PHONE_SANYOOTHERS,
                            },
              'SCP-2400': { 'module': 'com_sanyo2400',
                            'carrier': [c_sprint],
                            'brand': b_sanyo,
                            'helpid': helpids.ID_PHONE_SANYOOTHERS,
                            },
              'SCP-3100': { 'module': 'com_sanyo3100',
                            'carrier': [c_sprint],
                            'brand': b_sanyo,
                            'helpid': helpids.ID_PHONE_SANYOOTHERS,
                            },
              'SCP-3200': { 'module': 'com_sanyo3200',
                            'carrier': [c_sprint],
                            'brand': b_sanyo,
                            'helpid': helpids.ID_PHONE_SANYOOTHERS,
                                      },
              'SCP-4900': { 'module': 'com_sanyo4900',
                            'carrier': [c_sprint],
                            'brand': b_sanyo,
                            'helpid': helpids.ID_PHONE_SANYOOTHERS,
                            },
              'SCP-5300': { 'module': 'com_sanyo5300',
                            'carrier': [c_sprint],
                            'brand': b_sanyo,
                            'helpid': helpids.ID_PHONE_SANYOOTHERS,
                            },
              'SCP-5400': { 'module': 'com_sanyo5400',
                            'carrier': [c_sprint],
                            'brand': b_sanyo,
                            'helpid': helpids.ID_PHONE_SANYOOTHERS,
                            },
              'SCP-5500': { 'module': 'com_sanyo5500',
                            'carrier': [c_sprint],
                            'brand': b_sanyo,
                            'helpid': helpids.ID_PHONE_SANYOOTHERS,
                            },
              'SCP-7050': { 'module': 'com_sanyo7050',
                             'carrier': [c_sprint],
                             'brand': b_sanyo,
                             'helpid': helpids.ID_PHONE_SANYOOTHERS,
                             },
              'SCP-7200': { 'module': 'com_sanyo7200',
                            'carrier': [c_sprint],
                            'brand': b_sanyo,
                            'helpid': helpids.ID_PHONE_SANYOOTHERS,
                            },
              'SCP-7300': { 'module': 'com_sanyo7300',
                            'carrier': [c_sprint],
                            'brand': b_sanyo,
                            'helpid': helpids.ID_PHONE_SANYOOTHERS,
                            },
              'SCP-8100': { 'module': 'com_sanyo8100',
                            'carrier': [c_sprint],
                            'brand': b_sanyo,
                            'helpid': helpids.ID_PHONE_SANYOOTHERS,
                            },
              'SCP-8100 (Bell)': { 'module': 'com_sanyo8100_bell',
                                   'carrier': [c_bell],
                                   'brand': b_sanyo,
                                   'helpid': helpids.ID_PHONE_SANYOOTHERS,
                                   },
              'SCH-A310': { 'module': 'com_samsungscha310',
                            'carrier': [c_vzw],
                            'brand': b_samsung,
                            'helpid': None,
                            },
              'SPH-A460': { 'module': 'com_samsungspha460',
                            'brand': b_samsung,
                            'helpid': helpids.ID_PHONE_SAMSUNGOTHERS,
                            },
              'SPH-A620 (VGA1000)': { 'module': 'com_samsungspha620',
                                      'carrier': [c_sprint],
                                      'brand': b_samsung,
                                      'helpid': helpids.ID_PHONE_SAMSUNGOTHERS,
                                      },
              'SPH-A660 (VI660)': { 'module': 'com_samsungspha660',
                                    'carrier': [c_sprint],
                                    'brand': b_samsung,
                                    'helpid': helpids.ID_PHONE_SAMSUNGOTHERS,
                                    },
              'SPH-A680': { 'module': 'com_samsungspha680',
                            'carrier': [c_sprint],
                            'brand': b_samsung,
                            'helpid': helpids.ID_PHONE_SAMSUNGOTHERS,
                            },
              'SPH-A740': { 'module': 'com_samsungspha740',
                            'carrier': [c_sprint],
                            'brand': b_samsung,
                            'helpid': helpids.ID_PHONE_SAMSUNGOTHERS,
                            },
              'SPH-A840': { 'module': 'com_samsungspha840',
                            'carrier': [c_sprint],
                            'brand': b_samsung,
                            'helpid': helpids.ID_PHONE_SAMSUNGOTHERS,
                            },
              'SPH-A840 (Telus)': { 'module': 'com_samsungspha840_telus',
                                    'brand': b_samsung,
                                    'carrier': [c_telus],
                                    'helpid': helpids.ID_PHONE_SAMSUNGOTHERS,
                                    },
              'SPH-A900': { 'module': 'com_samsungspha900',
                            'carrier': [c_sprint],
                            'brand': b_samsung,
                            'helpid': helpids.ID_PHONE_SAMSUNGOTHERS,
                            },
              'SPH-M300PIM': { 'module': 'com_samsungsphm300pim',
                               'carrier': [c_sprint],
                               'brand': b_samsung,
                               'helpid': helpids.ID_PHONE_SAMSUNGSPHM300,
                               },
              'SPH-M300MEDIA': { 'module': 'com_samsungsphm300media',
                                 'carrier': [c_sprint],
                                 'brand': b_samsung,
                                 'helpid': helpids.ID_PHONE_SAMSUNGSPHM300,
                               },
              'SPH-N200': { 'module': 'com_samsungsphn200',
                            'carrier': [c_sprint],
                            'brand': b_samsung,
                            'helpid': helpids.ID_PHONE_SAMSUNGOTHERS,
                            },
              'SPH-N400': { 'module': 'com_samsungsphn400',
                            'carrier': [c_sprint],
                            'brand': b_samsung,
                            'helpid': helpids.ID_PHONE_SAMSUNGOTHERS,
                            },
              'SCH-A650': { 'module': 'com_samsungscha650',
                            'brand': b_samsung,
                            'carrier': [c_vzw],
                            'helpid': None,
                            },
              'SCH-A670': { 'module': 'com_samsungscha670',
                            'brand': b_samsung,
                            'carrier': [c_vzw],
                            'helpid': None,
                            },
              'SCH-A870': { 'module': 'com_samsungscha870',
                            'brand': b_samsung,
                            'carrier': [c_vzw],
                            'helpid': helpids.ID_PHONE_SAMSUNGSCHA870,
                            },
              'SCH-A950': { 'module': 'com_samsungscha950',
                            'brand': b_samsung,
                            'carrier': [c_vzw],
                            'helpid': helpids.ID_PHONE_SAMSUNGSCHA950,
                            },
              'SCH-A930': { 'module': 'com_samsungscha930',
                            'brand': b_samsung,
                            'carrier': [c_vzw],
                            'helpid': helpids.ID_PHONE_SAMSUNGSCHA930,
                            },
              'SCH-U470': { 'module': 'com_samsungschu470',
                            'brand': b_samsung,
                            'carrier': [c_vzw],
                            'helpid': helpids.ID_PHONE_SAMSUNGSCHU470,
                            },
              'SCH-U740': { 'module': 'com_samsungschu740',
                            'brand': b_samsung,
                            'carrier': [c_vzw],
                            'helpid': helpids.ID_PHONE_SAMSUNGSCHU740,
                            },
              'SCH-U750 (Alias 2)': { 'module': 'com_samsungschu750',
                            'brand': b_samsung,
                            'carrier': [c_vzw],
                            'helpid': helpids.ID_PHONE_SAMSUNGSCHU750,
                            },
              'SK6100' : { 'module': 'com_sk6100',
                           'brand': b_sk,
                           'carrier': [c_pelephone],
                           'helpid': None,
                           },
              'VM4050' : { 'module': 'com_toshibavm4050',
                           'brand': b_toshiba,
                           'carrier': [c_sprint],
                           'helpid': helpids.ID_PHONE_TOSHIBAVM4050,
                           },
              'VI-2300': { 'module': 'com_sanyo2300',
                           'carrier': [c_sprint],
                           'brand': b_sanyo,
                           'helpid': helpids.ID_PHONE_SANYOOTHERS,
                           },
              'V3m (Sprint)': { 'module': 'com_motov3m_sprint',
                                'brand': b_moto,
                                'carrier': [c_sprint],
                                'helpid': helpids.ID_PHONE_MOTOV3M,
                                },
              'LG-VI5225': { 'module': 'com_lgvi5225',
                             'carrier': [c_sti],
                             'brand': b_lg,
                             'helpid': None,
                             },
              'V710': { 'module': 'com_motov710',
                        'brand': b_moto,
                        'carrier': [c_vzw],
                        'helpid': helpids.ID_PHONE_MOTOV710,
                        },
              'V710m': { 'module': 'com_motov710m',
                         'brand': b_moto,
                         'carrier': [c_vzw],
                         'helpid': helpids.ID_PHONE_MOTOV710M,
                         },
              'V3c': { 'module': 'com_motov3c',
                       'brand': b_moto,
                       'carrier': [c_vzw],
                       'helpid': helpids.ID_PHONE_MOTOV3C,
                       },
              'V3cm': { 'module': 'com_motov3cm',
                        'brand': b_moto,
                        'carrier': [c_vzw],
                        'helpid': helpids.ID_PHONE_MOTOV3CM,
                        },
              'V3m': { 'module': 'com_motov3m',
                        'brand': b_moto,
                        'carrier': [c_vzw],
                        'helpid': helpids.ID_PHONE_MOTOV3M,
                        },
              'V3mM': { 'module': 'com_motov3mm',
                        'brand': b_moto,
                        'carrier': [c_vzw],
                        'helpid': helpids.ID_PHONE_MOTOV3MM,
                        },
              'V325': { 'module': 'com_motov325',
                        'brand': b_moto,
                        'carrier': [c_vzw],
                        'helpid': helpids.ID_PHONE_MOTOV325,
                        },
              'V325M': { 'module': 'com_motov325m',
                         'brand': b_moto,
                         'carrier': [c_vzw],
                         'helpid': helpids.ID_PHONE_MOTOV325M,
                        },
              'E815': { 'module': 'com_motoe815',
                        'brand': b_moto,
                        'carrier': [c_vzw],
                        'helpid': helpids.ID_PHONE_MOTOE815,
                        },
              'E815m': { 'module': 'com_motoe815m',
                         'brand': b_moto,
                         'carrier': [c_vzw],
                        'helpid': helpids.ID_PHONE_MOTOE815M,
                         },
              'K1m': { 'module': 'com_motok1m',
                       'brand': b_moto,
                       'carrier': [c_vzw],
                       'helpid': helpids.ID_PHONE_MOTOK1M,
                       },
              'Other CDMA phone': { 'module': 'com_othercdma',
                                    'carrier': [c_other],
                                    'brand': b_other,
                                    'helpid': None,
                                    },
              }

if __debug__:
    _phonedata.update( {'Audiovox CDM-8900': { 'module': 'com_audiovoxcdm8900',     # phone is too fragile for normal use
                                               'brand': b_audiovox,
                                               'helpid': None,
                                               },
                        'SPH-A790': { 'module': 'com_samsungspha790',
                                      'brand': b_samsung,
                                      'carrier': [c_sprint],
                                      'helpid': None,
                                      },
                        'RAZR V3t': { 'module': 'com_motov3t',
                                      'brand': b_moto,
                                      'carrier': [c_tmobileusa],
                                      'helpid': None,
                                      },
                        'SPH-A640': { 'module': 'com_samsungspha640',
                                      'carrier': [c_sprint],
                                      'brand': b_samsung,
                                      'helpid': helpids.ID_PHONE_SAMSUNGOTHERS,
                                      },
                        'LG-LX260 (Rumor)': {  'module': 'com_lglx260',
                                       'carrier': [c_sprint],
                                       'brand': b_lg,
                                       'helpid': None,
                                       }, 
                        })

# update the module path
for k, e in _phonedata.items():
    _phonedata[k]['module']=__name__+'.'+e['module']

phonemodels=_phonedata.keys()
phonemodels.sort()

def module(phone):
    return _phonedata[phone].get('module', None)

def carriers(phone):
    return _phonedata[phone].get('carrier', [c_other])

def manufacturer(phone):
    return _phonedata[phone].get('brand', b_other)

def helpid(phone):
    return _phonedata[phone].get('helpid', None)

_tmp1={}
_tmp2={}
for x in phonemodels:
    for y in carriers(x):
        _tmp1[y]=True
    _tmp2[manufacturer(x)]=True
phonecarriers=_tmp1.keys()
phonecarriers.sort()
phonemanufacturers=_tmp2.keys()
phonemanufacturers.sort()
del _tmp1, _tmp2

def phoneslist(brand=None, carrier_name=None):
    return [x for x in phonemodels if (brand is None or manufacturer(x)==brand) \
            and (carrier_name is None or carrier_name in carriers(x))]

def carrier2phones(carrier_name):
    # return the list of phone belongs to this carrier
    return [x for x in phonemodels if carrier_name in carriers(x)]

def manufacturer2phones(brand_name):
    # return a list of phone belongs to this brand
    return [x for x in phonemodels if manufacturer(x)==brand_name]

def getallmodulenames():
    return [_phonedata[k]['module'] for k in _phonedata]
